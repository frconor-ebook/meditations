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

  // Construct the fetch URL
  var fetchUrl = baseurl + '/_data/meditations.json';
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

  // Rest of your search logic...
  searchBox.addEventListener('input', function() {
    // ... your existing code ...
  });

  function displayResults(results) {
    // ... your existing code ...
  }
});