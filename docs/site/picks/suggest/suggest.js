/*
 * The public Community Picks suggestion form.
 *
 * Validates in the browser, then sends the finished suggestion straight into
 * the GitHub workflow -- as an issue, labelled pick:suggestion, exactly where
 * the review page and picks-build.yml already look. No email anywhere.
 *
 * Two routes, in order of preference:
 *
 * 1. SUBMIT_URL, when one is configured: a small receiver POSTs the issue on
 *    the visitor's behalf, so they need no GitHub account at all. GitHub Pages
 *    is static and cannot do this itself -- something has to hold a credential
 *    that can write to the repo, and that credential can never live in a
 *    public page. See workers/picks-submit.js for a ready-to-deploy receiver.
 *
 * 2. Otherwise, GitHub's own new-issue form, pre-filled from what was typed.
 *    Zero infrastructure and it lands in the same place; the cost is that the
 *    visitor needs a GitHub account, which the page says plainly.
 *
 * Either way the body is the shape quill/core/pick_suggestion.py produces, so
 * picks-build.yml parses one format however a suggestion arrived.
 */
(function () {
  "use strict";

  // Set this to a deployed receiver (workers/picks-submit.js) and the form
  // files the issue itself, with no GitHub account needed. Empty = fall back
  // to GitHub's own pre-filled new-issue form.
  var SUBMIT_URL = "";
  var REPO = "Community-Access/quill";

  var form = document.getElementById("suggest-form");
  var errorBox = document.getElementById("errors");
  var result = document.getElementById("result");
  if (!form) {
    return;
  }

  function value(id) {
    var el = document.getElementById(id);
    return el ? String(el.value || "").trim() : "";
  }

  function validate(pick) {
    var errors = [];
    if (!pick.title) {
      errors.push("Give it a name — what would you call it in a list?");
    }
    if (!pick.url) {
      errors.push(
        pick.type === "podcast" ? "Add the feed address." : "Add the stream address."
      );
    } else if (
      pick.url.toLowerCase().indexOf("https://") !== 0 &&
      pick.url.toLowerCase().indexOf("http://") !== 0
    ) {
      // http is accepted deliberately: many community stations are http-only.
      errors.push("The address should start with https:// or http://.");
    } else if (pick.url.indexOf(" ") !== -1) {
      errors.push("The address has a space in it. Check it was pasted whole.");
    }
    if (!pick.description) {
      errors.push(
        "Add a description. It is what people read when they are deciding."
      );
    }
    return errors;
  }

  function showErrors(errors) {
    // textContent throughout: nothing typed into this page is ever parsed as
    // markup. Same rule as the review page, for the same reason.
    errorBox.textContent = "";
    if (!errors.length) {
      return;
    }
    var heading = document.createElement("p");
    heading.textContent =
      errors.length === 1
        ? "There is one thing to fix:"
        : "There are " + errors.length + " things to fix:";
    errorBox.appendChild(heading);
    var list = document.createElement("ul");
    errors.forEach(function (message) {
      var item = document.createElement("li");
      item.textContent = message;
      list.appendChild(item);
    });
    errorBox.appendChild(list);
    errorBox.focus();
  }

  function issueTitle(pick) {
    return "[Pick] " + (pick.type === "podcast" ? "Podcast" : "Station") + ": " + pick.title;
  }

  function issueBody(pick) {
    var payload = { type: pick.type, title: pick.title };
    if (pick.description) payload.description = pick.description;
    if (pick.language) payload.language = pick.language;
    if (pick.collection) payload.collection = pick.collection;
    payload[pick.type === "podcast" ? "feed_url" : "stream_url"] = pick.url;

    var lines = [
      "**" + pick.title + "** -- suggested for the Community Picks list.",
      "",
      "- Kind: " + pick.type,
      "- Address: " + pick.url
    ];
    if (pick.description) lines.push("- Description: " + pick.description);
    if (pick.language) lines.push("- Language: " + pick.language);
    if (pick.collection) lines.push("- Suggested group: " + pick.collection);
    if (pick.why) lines.push("", "Why it belongs:", "", pick.why);
    lines.push("", "_Submitted from quillforall.org._", "");
    lines.push(
      "<!-- picks-build.yml reads the block below. Edit it, not the prose, " +
        "to change what lands in the catalogue. -->"
    );
    lines.push("```json pick");
    lines.push(JSON.stringify(payload, null, 2));
    lines.push("```");
    return lines.join("\n");
  }

  function succeed(message, detail) {
    result.textContent = "";
    var p = document.createElement("p");
    p.textContent = message;
    result.appendChild(p);
    if (detail) {
      var small = document.createElement("p");
      small.textContent = detail;
      result.appendChild(small);
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var pick = {
      type: value("kind") || "stream",
      title: value("title"),
      url: value("url"),
      description: value("description"),
      language: value("language"),
      collection: value("collection"),
      why: value("why")
    };

    var errors = validate(pick);
    if (errors.length) {
      showErrors(errors);
      return;
    }
    errorBox.textContent = "";

    var title = issueTitle(pick);
    var body = issueBody(pick);

    if (SUBMIT_URL) {
      fetch(SUBMIT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title, body: body })
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("rejected");
          }
          succeed(
            "Thank you — your suggestion was sent.",
            "A person reads every one. Approved suggestions appear in the app within a day."
          );
          form.reset();
        })
        .catch(function () {
          succeed(
            "That could not be sent just now.",
            "Please try again shortly, or use one of the other ways listed below."
          );
        });
      return;
    }

    // No receiver configured: hand it to GitHub's own new-issue form, already
    // filled in. It lands as a labelled issue, which is the whole point --
    // reviewable on the review page and picked up by picks-build.yml.
    var href =
      "https://github.com/" +
      REPO +
      "/issues/new?labels=pick%3Asuggestion&title=" +
      encodeURIComponent(title) +
      "&body=" +
      encodeURIComponent(body);
    window.open(href, "_blank", "noopener");
    succeed(
      "Your suggestion is ready on GitHub in a new tab — press Submit new issue there to send it.",
      "That step needs a GitHub account. If you do not have one, Quill Radio itself can send the suggestion for you with no account at all."
    );
  });
})();
