document.addEventListener('DOMContentLoaded', function() {
  var searchBox = document.getElementById('search-box');
  var searchResults = document.getElementById('search-results');
  var meditations = [];

  // Get baseurl from data attribute, with fallback to empty string
  var baseurl = document.body.dataset.baseurl || '';

  // Remove trailing slash from baseurl if present
  if (baseurl.endsWith('/')) {
    baseurl = baseurl.slice(0, -1);
  }
// Construct the fetch URL without adding an extra slash
fetchUrl = baseurl + '/data/meditations.json'; // Update this line

  console.log("Fetching data from:", fetchUrl);

  fetch(fetchUrl)
    .then(response => {
      console.log("Response status:", response.status);
      if (!response.ok) {
        // Log the response text for debugging
        return response.text().then(text => {
          console.error("Response text:", text);
          throw new Error('Network response was not ok, status: ' + response.status);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log("Fetched data:", data);
      meditations = data;
    })
    .catch(error => {
      console.error('Error fetching meditations data:', error);
      searchResults.innerHTML = '<p>Error loading meditations data. See console for details.</p>';
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