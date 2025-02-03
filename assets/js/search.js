document.addEventListener('DOMContentLoaded', function() {
  var searchBox = document.getElementById('search-box');
  var searchResults = document.getElementById('search-results');
  var meditations = [];

  // Fetch the meditations data using baseurl
  var baseurl = document.body.dataset.baseurl; // Get baseurl from data attribute
  fetch(baseurl + '/_data/meditations.json')
    .then(response => response.json())
    .then(data => {
      meditations = data;
    })
    .catch(error => {
      console.error('Error fetching meditations data:', error);
    });

  searchBox.addEventListener('input', function() {
    var searchTerm = searchBox.value.toLowerCase();

    // Filter meditations based on search term
    var filteredMeditations = meditations.filter(function(meditation) {
      return meditation.title.toLowerCase().includes(searchTerm) ||
             meditation.content.toLowerCase().includes(searchTerm);
    });

    displayResults(filteredMeditations);
  });

  function displayResults(results) {
    searchResults.innerHTML = '';

    if (results.length === 0) {
      var noResultsItem = document.createElement('p');
      noResultsItem.textContent = 'No results found.';
      searchResults.appendChild(noResultsItem);
    } else {
      var resultsList = document.createElement('ul');
      results.forEach(function(meditation) {
        var listItem = document.createElement('li');
        var link = document.createElement('a');
        // Use the baseurl for links
        link.href = baseurl + '/homilies/' + meditation.slug + '/';
        link.textContent = meditation.title;
        listItem.appendChild(link);
        resultsList.appendChild(listItem);
      });
      searchResults.appendChild(resultsList);
    }
  }
});