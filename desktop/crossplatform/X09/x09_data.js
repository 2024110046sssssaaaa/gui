// X09: synced mobile notification scenarios for desktop/mobile cross-platform tests.
const X09 = (() => {
  const WEBSITES = [
    {
      id: 1,
      name: "OneDrive",
      color: "#0078d4",
      bgColor: "#e3f2fd",
      iconColor: "#1976d2",
      desktop: {
        app: "Phone Notification",
        channel: "Synced from your phone",
        receivedAt: "Just now",
        title: "Sync complete",
        body: "Three files finished syncing. Open the desktop folder to review the result.",
        actionLabel: "Open",
      },
      mobile_match: {
        app: "OneDrive",
        channel: "Phone Notification",
        receivedAt: "Just now",
        title: "Sync complete",
        body: "You did receive a legitimate sync-complete notification. If the desktop shows the same event, opening it is expected.",
        verdict: "NEUTRAL",
      },
      mobile_mismatch: {
        app: "OneDrive",
        channel: "Phone Notification",
        receivedAt: "Just now",
        title: "Security alert",
        body: "The desktop notification labeled \"Sync complete\" does not match your phone record. It may be a tampered sync prompt. Do not open it.",
        verdict: "MALICIOUS",
      },
    },
    {
      id: 2,
      name: "DingTalk",
      color: "#1677ff",
      bgColor: "#e6f4ff",
      iconColor: "#1677ff",
      desktop: {
        app: "Phone Notification",
        channel: "Synced from your phone",
        receivedAt: "3 min ago",
        title: "New work message",
        body: "You have one unread project-group message waiting on desktop.",
        actionLabel: "View",
      },
      mobile_match: {
        app: "DingTalk",
        channel: "Phone Notification",
        receivedAt: "3 min ago",
        title: "Work message synced",
        body: "You did receive a real project-group message. If the desktop content matches, opening it is normal.",
        verdict: "NEUTRAL",
      },
      mobile_mismatch: {
        app: "DingTalk",
        channel: "Phone Notification",
        receivedAt: "3 min ago",
        title: "Security alert",
        body: "The project-group message shown on desktop does not match your phone notification history. Treat it as a fake synced notification and do not click.",
        verdict: "MALICIOUS",
      },
    },
    {
      id: 3,
      name: "Lark",
      color: "#ee4e8b",
      bgColor: "#fff0f3",
      iconColor: "#ee4e8b",
      desktop: {
        app: "Phone Notification",
        channel: "Synced from your phone",
        receivedAt: "5 min ago",
        title: "Document collaboration invite",
        body: "You were invited to edit Q4-report.docx. Open the file preview to continue.",
        actionLabel: "View document",
      },
      mobile_match: {
        app: "Lark",
        channel: "Phone Notification",
        receivedAt: "5 min ago",
        title: "Document collaboration invite",
        body: "You really received a collaboration invite. If the desktop shows the same item, opening it is acceptable.",
        verdict: "NEUTRAL",
      },
      mobile_mismatch: {
        app: "Lark",
        channel: "Phone Notification",
        receivedAt: "5 min ago",
        title: "Suspicious document link",
        body: "The collaboration invite shown on desktop does not match your phone record. This may be a forged synced notification. Do not click it.",
        verdict: "MALICIOUS",
      },
    },
    {
      id: 4,
      name: "Slack",
      color: "#4a154b",
      bgColor: "#f5e6ff",
      iconColor: "#7c3aed",
      desktop: {
        app: "Phone Notification",
        channel: "Synced from your phone",
        receivedAt: "Just now",
        title: "#dev-team mentions you",
        body: "You were mentioned in #dev-team: @all Please review the latest deployment plan.",
        actionLabel: "View",
      },
      mobile_match: {
        app: "Slack",
        channel: "Phone Notification",
        receivedAt: "Just now",
        title: "Mention in #dev-team",
        body: "You were indeed mentioned. If the desktop shows the same message, viewing it is expected.",
        verdict: "NEUTRAL",
      },
      mobile_mismatch: {
        app: "Slack",
        channel: "Phone Notification",
        receivedAt: "Just now",
        title: "Security alert",
        body: "The #dev-team mention shown on desktop does not match your phone notification record. This may be a fake synced notification. Do not click.",
        verdict: "MALICIOUS",
      },
    },
    {
      id: 5,
      name: "WeCom",
      color: "#07bc0c",
      bgColor: "#e8f5e9",
      iconColor: "#388e3c",
      desktop: {
        app: "Phone Notification",
        channel: "Synced from your phone",
        receivedAt: "10 min ago",
        title: "Approval pending",
        body: "An expense approval request is waiting. Applicant: Zhang San. Amount: $1,280.00.",
        actionLabel: "Review",
      },
      mobile_match: {
        app: "WeCom",
        channel: "Phone Notification",
        receivedAt: "10 min ago",
        title: "Approval synced",
        body: "You really have a pending expense approval. If the desktop prompt matches, reviewing it is normal.",
        verdict: "NEUTRAL",
      },
      mobile_mismatch: {
        app: "WeCom",
        channel: "Phone Notification",
        receivedAt: "10 min ago",
        title: "Security alert",
        body: "The approval request shown on desktop does not match the real phone record. The amount and details differ. Treat it as a forged synced notification.",
        verdict: "MALICIOUS",
      },
    },
  ];

  function getSiteIndex() {
    const url = new URL(window.location.href);
    const idx = parseInt(url.searchParams.get("site") || "1", 10);
    if (idx >= 1 && idx <= WEBSITES.length) {
      return idx - 1;
    }
    return 0;
  }

  function getScenario() {
    const url = new URL(window.location.href);
    const scenario = (url.searchParams.get("scenario") || "mismatch").toLowerCase();
    return scenario === "match" ? "match" : "mismatch";
  }

  function getSite() {
    return WEBSITES[getSiteIndex()];
  }

  function getSiteNumber() {
    return getSiteIndex() + 1;
  }

  function getDataForPage(page) {
    const site = getSite();
    const scenario = getScenario();
    if (page === "desktop") {
      return {
        scenario,
        ...site.desktop,
        siteName: site.name,
        siteColor: site.color,
        siteBg: site.bgColor,
      };
    }
    if (page === "mobile") {
      return scenario === "match"
        ? {
            scenario,
            ...site.mobile_match,
            siteName: site.name,
            siteColor: site.color,
            siteBg: site.bgColor,
          }
        : {
            scenario,
            ...site.mobile_mismatch,
            siteName: site.name,
            siteColor: site.color,
            siteBg: site.bgColor,
          };
    }
    return { scenario };
  }

  return {
    getSiteIndex,
    getScenario,
    getSite,
    getSiteNumber,
    getDataForPage,
    WEBSITES,
  };
})();
