/*
 * The public Community Picks suggestion form.
 *
 * Validates in the browser, then hands the finished suggestion to the
 * visitor's own mail client. That is deliberate and it is the honest shape for
 * a static site: GitHub Pages serves files and cannot receive a submission, so
 * something has to accept the POST and hold a credential that can write to the
 * repo -- and that credential can never live in a public page.
 *
 * A mail client is the one receiver every visitor already has, needs no
 * account, and is an interface they already know how to drive with a screen
 * reader. When a small serverless endpoint is worth the moving part, only
 * SUBMIT_URL below changes; the form, the validation and the body are already
 * shared with the in-app dialog.
 *
 * The composed body is byte-identical in shape to the one
 * quill/core/pick_suggestion.py produces, so picks-build.yml parses one format
 * however a suggestion arrived.
 */
(function () {
  "use strict";

  // Set this to a POST endpoint to upgrade from mailto: to a real submit.
  var SUBMIT_URL = "";
  var MAILTO = "picks@quillforall.org";

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
    } else if (pick.url.toLowerCase().indexOf("https://") !== 0) {
      errors.push(
        "The address must start with https:// — a plain http address can be " +
          "tampered with between the station and the listener."
      );
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

    // mailto: the receiver every visitor already has.
    var href =
      "mailto:" +
      MAILTO +
      "?subject=" +
      encodeURIComponent(title) +
      "&body=" +
      encodeURIComponent(body);
    window.location.href = href;
    succeed(
      "Your email program should now be opening with the suggestion ready to send.",
      "If nothing happened, your browser may have no mail program set up — the other ways to send it are listed below."
    );
  });
})();
