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
  var STOPWORDS = new Set(['a', 'an', 'and', 'as', 'at', 'be', 'by', 'for',
    'in', 'is', 'it', 'of', 'on', 'or', 'that', 'the', 'this', 'to', 'was', 'with']);
  var mini = null;
  var indexPromise = null;

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(baseurl + '/data/search_index.json')
        .then(function(response) {
          if (!response.ok) throw new Error('HTTP ' + response.status);
          return response.json();
        })
        .then(function(docs) {
          var ms = new MiniSearch({
            idField: 'slug',
            fields: ['title', 'excerpt'],
            storeFields: ['title', 'slug', 'excerpt'],
            processTerm: function(term) {
              term = term.toLowerCase();
              return STOPWORDS.has(term) ? null : term;
            },
            searchOptions: {
              boost: { title: 3 },
              prefix: true,
              fuzzy: 0.15,
              combineWith: 'AND'
            }
          });
          ms.addAll(docs);
          mini = ms;
        });
    }
    return indexPromise;
  }

  // Start fetching the index as soon as the user shows intent to search
  searchBox.addEventListener('focus', function() {
    loadIndex().catch(function() {});
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

    if (!mini) {
      showStatus('Loading search index…');
      loadIndex().then(runSearch).catch(function(error) {
        console.error('Error loading search index:', error);
        showStatus('Error loading search index. Please try again later.');
      });
      return;
    }

    var results = mini.search(query);
    if (results.length === 0) {
      // All-terms match failed; fall back to any-term so near misses still surface
      results = mini.search(query, { combineWith: 'OR' });
    }
    displayResults(results, query);
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
    searchResults.innerHTML = '';

    if (results.length === 0) {
      searchResults.appendChild(
        makeStatus('No results for “' + query + '”.')
      );
      return;
    }

    searchResults.appendChild(
      makeStatus(results.length + (results.length === 1 ? ' result' : ' results'))
    );

    var list = document.createElement('ul');
    list.className = 'search-results-list';

    results.slice(0, MAX_RESULTS).forEach(function(result) {
      var item = document.createElement('li');

      var link = document.createElement('a');
      link.href = baseurl + '/homilies/' + result.slug + '/';
      appendHighlighted(link, result.title, result.terms);
      item.appendChild(link);

      var snippetText = makeSnippet(result.excerpt, result.terms);
      if (snippetText) {
        var snippet = document.createElement('p');
        snippet.className = 'search-snippet';
        appendHighlighted(snippet, snippetText, result.terms);
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
  }

  // Regex matching any of the matched terms as a word prefix
  function termPattern(terms) {
    var escaped = (terms || [])
      .filter(function(term) { return term.length > 1; })
      .map(function(term) {
        return term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      });
    if (escaped.length === 0) return null;
    return new RegExp('\\b(?:' + escaped.join('|') + ')\\w*', 'gi');
  }

  // Append text to el with matched terms wrapped in <mark>
  function appendHighlighted(el, text, terms) {
    var pattern = termPattern(terms);
    if (!pattern) {
      el.appendChild(document.createTextNode(text));
      return;
    }
    var lastIndex = 0;
    var match;
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        el.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      }
      var mark = document.createElement('mark');
      mark.textContent = match[0];
      el.appendChild(mark);
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      el.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
  }

  // A short window of the excerpt around the first matched term
  function makeSnippet(excerpt, terms) {
    if (!excerpt) return '';

    var pattern = termPattern(terms);
    var pos = 0;
    if (pattern) {
      var match = pattern.exec(excerpt);
      if (match) pos = match.index;
    }

    var start = 0;
    if (pos > 60) {
      start = excerpt.lastIndexOf(' ', pos - 60);
      if (start < 0) start = 0;
    }
    var end = Math.min(excerpt.length, pos + 180);
    var endSpace = excerpt.indexOf(' ', end);
    if (endSpace !== -1) end = endSpace;

    var text = excerpt.slice(start, end).trim();
    if (start > 0) text = '…' + text;
    if (end < excerpt.length) text += '…';
    return text;
  }
});
