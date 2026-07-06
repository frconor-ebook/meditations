document.addEventListener('DOMContentLoaded', function() {
  var searchBox = document.getElementById('search-box');
  var searchResults = document.getElementById('search-results');

  // Only the homepage has a search box; do nothing (and fetch nothing) elsewhere
  if (!searchBox || !searchResults) return;

  var baseurl = document.body.dataset.baseurl || '';
  if (baseurl.endsWith('/')) {
    baseurl = baseurl.slice(0, -1);
  }

  var MAX_RESULTS = 30;
  var pagefind = null;
  var loadPromise = null;

  // Pagefind indexes the full text of every meditation at build time and
  // serves it in small chunks, so nothing heavy loads until someone searches
  function loadPagefind() {
    if (!loadPromise) {
      loadPromise = import(baseurl + '/pagefind/pagefind.js').then(function(pf) {
        return Promise.resolve(pf.options({ baseUrl: baseurl + '/' })).then(function() {
          pf.init();
          pagefind = pf;
        });
      });
    }
    return loadPromise;
  }

  // Start loading as soon as the user shows intent to search
  searchBox.addEventListener('focus', function() {
    loadPagefind().catch(function() {});
  }, { once: true });

  var debounceTimer = null;
  searchBox.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 120);
  });

  function runSearch() {
    var query = searchBox.value.trim();

    if (query === '') {
      searchResults.innerHTML = '';
      return;
    }

    if (!pagefind) {
      showStatus('Loading search…');
      loadPagefind().then(runSearch).catch(function(error) {
        console.error('Error loading search:', error);
        showStatus('Error loading search. Please try again later.');
      });
      return;
    }

    // Multi-word queries: run an exact-phrase search alongside the broad
    // word search and rank exact matches first — someone recalling a phrase
    // from mid-meditation gets that meditation at the top
    var wantsPhrase = query.indexOf(' ') !== -1 && query.indexOf('"') === -1;
    Promise.all([
      wantsPhrase ? pagefind.search('"' + query + '"') : Promise.resolve(null),
      pagefind.search(query)
    ]).then(function(res) {
      if (searchBox.value.trim() !== query) return; // superseded by newer input
      var exact = res[0] ? res[0].results : [];
      var seen = {};
      exact.forEach(function(r) { seen[r.id] = true; });
      var broad = (res[1] ? res[1].results : []).filter(function(r) {
        return !seen[r.id];
      });
      displayResults(exact.concat(broad), query);
    }).catch(function(error) {
      console.error('Search error:', error);
      showStatus('Search failed. Please try again.');
    });
  }

  function showStatus(message) {
    searchResults.innerHTML = '';
    searchResults.appendChild(makeStatus(message));
  }

  function makeStatus(message) {
    var status = document.createElement('p');
    status.className = 'search-status';
    status.textContent = message;
    return status;
  }

  function displayResults(results, query) {
    if (results.length === 0) {
      showStatus('No results for “' + query + '”. Search matches whole words — ' +
        'check the spelling or try a different word.');
      return;
    }

    // Fetch details for the results we will show
    Promise.all(
      results.slice(0, MAX_RESULTS).map(function(result) { return result.data(); })
    ).then(function(pages) {
      // The query may have changed while page data was loading
      if (searchBox.value.trim() !== query) return;

      searchResults.innerHTML = '';
      searchResults.appendChild(
        makeStatus(results.length + (results.length === 1 ? ' result' : ' results'))
      );

      var list = document.createElement('ul');
      list.className = 'search-results-list';

      pages.forEach(function(page) {
        var item = document.createElement('li');

        var link = document.createElement('a');
        link.href = page.url;
        link.textContent = (page.meta && page.meta.title) || page.url;
        item.appendChild(link);

        if (page.excerpt) {
          var snippet = document.createElement('p');
          snippet.className = 'search-snippet';
          // Pagefind excerpts are escaped text from our own pages with
          // <mark> tags around matched terms
          snippet.innerHTML = page.excerpt;
          item.appendChild(snippet);
        }

        list.appendChild(item);
      });
      searchResults.appendChild(list);

      if (results.length > MAX_RESULTS) {
        searchResults.appendChild(
          makeStatus('Showing the first ' + MAX_RESULTS + ' results.')
        );
      }
    });
  }
});
