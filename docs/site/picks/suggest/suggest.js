/*
 * The public Community Picks suggestion form.
 *
 * Validates in the browser, then POSTs the finished suggestion to the
 * feedback-hub submission server, which files it as an issue labelled
 * pick:suggestion -- exactly where the review page and picks-build.yml already
 * look. The visitor needs no GitHub account and no sign-in of any kind. No
 * email anywhere.
 *
 * Why a server at all: GitHub Pages is static. It serves files; it cannot
 * receive a submission. Something has to accept the POST and hold a credential
 * that can write to the repo, and that credential can never live in a public
 * page -- GitHub's own secret scanning would revoke a published token within
 * minutes, rightly. So the question was never "server or no server", it was
 * whose small process. The answer is feedback_hub.server, deployed on
 * lp.csedesigns.com; see deploy/README.md in the feedback-hub repository.
 *
 * The body is the shape quill/core/pick_suggestion.py produces, so
 * picks-build.yml parses one format however a suggestion arrived -- from here,
 * from the in-app dialog, or typed by hand into a GitHub issue.
 *
 * Accessibility notes are inline rather than gathered here, next to the code
 * that would otherwise be "simplified" back into a bug. The three that matter
 * most: focus, not role="alert", carries errors; the live region is cleared on
 * one tick and written on the next; the submit button is never `disabled`.
 */
(function () {
  "use strict";

  // The receiver that files the issue on the visitor's behalf. Its origin must
  // also appear in this page's connect-src, or the browser blocks the request
  // before it leaves and the form looks broken while everything works.
  var SUBMIT_URL = "https://lp.csedesigns.com/submit/picks";

  var form = document.getElementById("suggest-form");
  var errorBox = document.getElementById("errors");
  var result = document.getElementById("result");
  var submitButton = document.getElementById("send");
  var sendStatus = document.getElementById("send-status");
  if (!form) {
    return;
  }

  var sending = false;
  var announceTimer = null;

  var FIELD_LABELS = {
    kind: "What is it?",
    title: "Name",
    url: "Address",
    description: "Description",
    language: "Language",
    collection: "Which group does it belong in?",
    why: "Why does it belong?"
  };

  var MAX_DESCRIPTION = 600;
  var MAX_WHY = 600;

  // Captured once, at load. Restoring from this snapshot is why a field's hint
  // id can never be lost, however many times it goes in and out of error.
  var BASE_DESCRIBEDBY = {};
  Object.keys(FIELD_LABELS).forEach(function (id) {
    var el = document.getElementById(id);
    if (el) {
      BASE_DESCRIBEDBY[id] = el.getAttribute("aria-describedby") || "";
    }
  });

  function value(id) {
    var el = document.getElementById(id);
    return el ? String(el.value || "").trim() : "";
  }

  // ---- the one live region -------------------------------------------------

  function announce(text) {
    if (announceTimer) {
      window.clearTimeout(announceTimer);
      announceTimer = null;
    }
    // Clear now, write on a later tick. That commits the empty state to the
    // accessibility tree, which is what lets a repeated identical string --
    // two rate-limit refusals in a row, say -- register as a change instead of
    // being swallowed as "no change since last time".
    sendStatus.textContent = "";
    announceTimer = window.setTimeout(function () {
      announceTimer = null;
      sendStatus.textContent = text;
    }, 150);
  }

  function silence() {
    if (announceTimer) {
      window.clearTimeout(announceTimer);
      announceTimer = null;
    }
    sendStatus.textContent = "";
  }

  function setSending(on) {
    sending = on;
    // aria-disabled, never the disabled property. Disabling the element that
    // currently has focus blurs it and sets no sequential starting point, so
    // the next Tab restarts from the top of the document -- thirteen stops
    // back through every field just filled in, announced by nothing. The
    // `sending` guard above is what actually prevents a second send.
    if (on) {
      submitButton.setAttribute("aria-disabled", "true");
    } else {
      submitButton.removeAttribute("aria-disabled");
    }
  }

  // ---- per-field error state ----------------------------------------------

  function setFieldError(id, message) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    var errId = id + "-error";
    var node = document.getElementById(errId);
    if (!node) {
      node = document.createElement("span");
      node.id = errId;
      node.className = "field-error";
      el.parentNode.insertBefore(node, el);
    }
    node.textContent = "";
    // "Error:" as a real element, not a CSS ::before. Screen readers announce
    // generated content, and a DOM <strong> is also the only cue that survives
    // Windows High Contrast, where author colours are discarded.
    var tag = document.createElement("strong");
    tag.textContent = "Error:";
    node.appendChild(tag);
    node.appendChild(document.createTextNode(" " + message));
    el.setAttribute("aria-invalid", "true");
    // The error id first, so on re-focus the problem is heard before the hint.
    var base = BASE_DESCRIBEDBY[id];
    el.setAttribute("aria-describedby", base ? errId + " " + base : errId);
  }

  function clearFieldError(id) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.removeAttribute("aria-invalid");
    var base = BASE_DESCRIBEDBY[id];
    if (base) {
      el.setAttribute("aria-describedby", base);
    } else {
      el.removeAttribute("aria-describedby");
    }
    var node = document.getElementById(id + "-error");
    if (node && node.parentNode) {
      node.parentNode.removeChild(node);
    }
  }

  function clearAllFieldErrors() {
    Object.keys(FIELD_LABELS).forEach(clearFieldError);
  }

  // Cleared on input, not on blur. Clearing is silent; re-validating on blur
  // would interrupt every time somebody tabs past a field they are not done
  // with yet.
  Object.keys(FIELD_LABELS).forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) {
      return;
    }
    var handler = function () {
      if (el.getAttribute("aria-invalid") === "true") {
        clearFieldError(id);
      }
    };
    el.addEventListener("input", handler);
    el.addEventListener("change", handler);
  });

  // ---- validation ----------------------------------------------------------

  function validate(pick) {
    var errors = [];
    function fail(field, message) {
      errors.push({ field: field, message: message });
    }

    if (!pick.title) {
      fail("title", "Give it a name — what would you call it in a list?");
    }
    if (!pick.url) {
      fail("url", pick.type === "podcast" ? "Add the feed address." : "Add the stream address.");
    } else if (
      pick.url.toLowerCase().indexOf("https://") !== 0 &&
      pick.url.toLowerCase().indexOf("http://") !== 0
    ) {
      // http is accepted deliberately: many community stations are http-only.
      fail("url", "The address should start with https:// or http://.");
    } else if (pick.url.indexOf(" ") !== -1) {
      fail("url", "The address has a space in it. Check it was pasted whole.");
    }
    if (!pick.description) {
      fail("description", "Add a description. It is what people read when they are deciding.");
    } else if (pick.description.length > MAX_DESCRIPTION) {
      fail(
        "description",
        "The description is " + (pick.description.length - MAX_DESCRIPTION) +
          " characters too long. The limit is " + MAX_DESCRIPTION + "."
      );
    }
    if (pick.why.length > MAX_WHY) {
      fail(
        "why",
        "That is " + (pick.why.length - MAX_WHY) + " characters too long. The limit is " +
          MAX_WHY + "."
      );
    }
    return errors;
  }

  // ---- error summary -------------------------------------------------------

  function showErrors(errors) {
    // textContent throughout: nothing typed into this page is ever parsed as
    // markup. Same rule as the review page, for the same reason.
    errorBox.textContent = "";
    clearAllFieldErrors();
    if (!errors.length) {
      return;
    }

    // A heading is the focus target, not the container. Focusing the container
    // makes a screen reader read the whole list in one uninterruptible breath;
    // focusing the heading says how many there are and hands the reading back.
    var heading = document.createElement("h3");
    heading.setAttribute("tabindex", "-1");
    heading.className = "focus-target";
    heading.textContent =
      errors.length === 1 ? "There is one thing to fix" : "There are " + errors.length + " things to fix";
    errorBox.appendChild(heading);

    var list = document.createElement("ul");
    errors.forEach(function (err) {
      setFieldError(err.field, err.message);
      var item = document.createElement("li");
      var link = document.createElement("a");
      link.href = "#" + err.field;
      link.textContent = FIELD_LABELS[err.field] + ": " + err.message;
      link.addEventListener("click", function (event) {
        // Explicit focus rather than trusting fragment navigation, so that
        // following the same link twice still works and #url stays out of the
        // address bar.
        event.preventDefault();
        var target = document.getElementById(err.field);
        if (target) {
          target.focus();
        }
      });
      item.appendChild(link);
      list.appendChild(item);
    });
    errorBox.appendChild(list);
    heading.focus();
  }

  // ---- the outcome, as a place rather than an announcement -----------------

  function finish(headingText, lines, failed) {
    silence();
    setSending(false);
    result.textContent = "";
    result.className = failed ? "result bad" : "result ok";

    var heading = document.createElement("h3");
    heading.setAttribute("tabindex", "-1");
    heading.className = "focus-target";
    var tag = document.createElement("strong");
    tag.textContent = failed ? "Not sent." : "Sent.";
    heading.appendChild(tag);
    heading.appendChild(document.createTextNode(" " + headingText));
    result.appendChild(heading);

    lines.forEach(function (line) {
      var p = document.createElement("p");
      p.textContent = line;
      result.appendChild(p);
    });
    heading.focus();
  }

  function messageFor(status) {
    if (status === 429) {
      return "Too many suggestions have come from here just now. Wait a minute, then press Send suggestion again.";
    }
    if (status === 403) {
      return "That was refused. Use one of the routes under the heading Other ways to send a suggestion.";
    }
    if (status === 400 || status === 413) {
      return "Something in the form was not accepted. Check the address and the name, then press Send suggestion again.";
    }
    return "The service is not answering. Press Send suggestion to try again shortly.";
  }

  // ---- the issue -----------------------------------------------------------

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

  // ---- submit --------------------------------------------------------------

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (sending) {
      return;
    }

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
    clearAllFieldErrors();
    result.textContent = "";
    result.className = "";

    setSending(true);

    // Nothing is announced yet. A round trip that finishes in eighty
    // milliseconds should produce one sentence -- the outcome -- rather than a
    // "Sending" that queues around it and leaves the visitor unsure which was
    // the last word.
    var sendingTimer = window.setTimeout(function () {
      announce("Sending your suggestion.");
    }, 500);
    var slowTimer = window.setTimeout(function () {
      announce("Still sending. This is taking longer than usual.");
    }, 10000);

    var controller = window.AbortController ? new window.AbortController() : null;
    var abortTimer = window.setTimeout(function () {
      if (controller) {
        controller.abort();
      }
    }, 20000);

    function settle() {
      window.clearTimeout(sendingTimer);
      window.clearTimeout(slowTimer);
      window.clearTimeout(abortTimer);
    }

    var options = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: issueTitle(pick), body: issueBody(pick) })
    };
    if (controller) {
      options.signal = controller.signal;
    }

    fetch(SUBMIT_URL, options)
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            return { ok: response.ok, status: response.status, data: data };
          });
      })
      .then(function (outcome) {
        settle();
        if (outcome.ok) {
          form.reset();
          // reset() only touches values. It leaves aria-invalid and the
          // injected error text behind, describing fields that are now empty.
          clearAllFieldErrors();
          errorBox.textContent = "";
          var lines = [];
          if (outcome.data && outcome.data.number) {
            // Its own sentence, so it survives being read in isolation.
            lines.push("It is suggestion number " + outcome.data.number + ".");
          }
          lines.push(
            "A person reads every one. Approved suggestions appear in the app within a day."
          );
          lines.push("Nothing else is needed from you.");
          finish(
            "Thank you — your " +
              (pick.type === "podcast" ? "podcast" : "radio station") +
              " suggestion was sent.",
            lines,
            false
          );
          return;
        }
        // Nothing is reset on failure. What was typed is the visitor's only
        // copy, and wiping it because the server answered 502 would be the
        // most punishing thing this page could do to somebody who filled it in
        // without visual scanning to help.
        finish(
          "That was not sent.",
          [messageFor(outcome.status), "Nothing you typed has been lost."],
          true
        );
      })
      .catch(function () {
        settle();
        finish(
          "That could not be sent.",
          [
            "Your device could not reach us. Check your connection, then press Send suggestion to try again.",
            "Nothing you typed has been lost."
          ],
          true
        );
      });
  });
})();
