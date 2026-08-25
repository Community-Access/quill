/*
 * The Community Picks review page.
 *
 * Static, serverless, and holding no secret of its own: authority is GitHub's,
 * so there is no permission logic here to get wrong. Only a token with write
 * access can label an issue -- the API simply refuses anything else.
 *
 * THE ONE RULE THAT MATTERS
 * -------------------------
 * Suggestions are written by the public and displayed on a page that holds a
 * token, so any script injection here steals it. Every field from an issue is
 * therefore rendered with textContent, NEVER innerHTML, and a URL is shown as
 * text unless it is plainly https, in which case it may become a link. The CSP
 * (connect-src api.github.com only) means a successful injection would have
 * nowhere to send the token anyway. Belt and braces, both cheap.
 *
 * Design: docs/design/community-picks.md
 */
(function () {
  "use strict";

  var REPO = "Community-Access/quill";
  var API = "https://api.github.com/repos/" + REPO;
  var KEY = "quill-picks-token";
  var SUGGESTION = "pick:suggestion";
  var APPROVED = "pick:approved";
  var DECLINED = "pick:declined";

  var token = "";
  var el = function (id) { return document.getElementById(id); };

  function say(message) {
    el("status").textContent = message;
  }

  function api(path, options) {
    var opts = options || {};
    return fetch(API + path, {
      method: opts.method || "GET",
      headers: {
        Authorization: "Bearer " + token,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json"
      },
      body: opts.body ? JSON.stringify(opts.body) : undefined
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("GitHub said " + response.status);
      }
      return response.status === 204 ? null : response.json();
    });
  }

  /* -- sign in ------------------------------------------------------------ */

  function storeToken(value, remember) {
    token = value;
    try {
      (remember ? localStorage : sessionStorage).setItem(KEY, value);
    } catch (e) {
      /* private mode: the token simply does not persist */
    }
  }

  function loadToken() {
    try {
      return sessionStorage.getItem(KEY) || localStorage.getItem(KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function signOut() {
    token = "";
    try {
      sessionStorage.removeItem(KEY);
      localStorage.removeItem(KEY);
    } catch (e) { /* nothing to clear */ }
    el("signed-in").hidden = true;
    el("signin-section").hidden = false;
    el("token").value = "";
    el("token").focus();
  }

  function signIn(value, remember) {
    token = value;
    return fetch("https://api.github.com/user", {
      headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" }
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("that token was not accepted");
        }
        return response.json();
      })
      .then(function (user) {
        storeToken(value, remember);
        el("signin-section").hidden = true;
        el("signed-in").hidden = false;
        el("who").textContent = "Signed in as " + String(user.login || "") + ". ";
        return load();
      });
  }

  /* -- the list ------------------------------------------------------------ */

  function pickBlock(body) {
    // Mirrors core/pick_suggestion.parse_issue_body: exactly one block, or we
    // refuse to guess. An issue edited into two is one for a person to read.
    var matches = String(body || "").match(/```json pick\s*([\s\S]*?)\s*```/g);
    if (!matches || matches.length !== 1) {
      return null;
    }
    var inner = matches[0].replace(/```json pick\s*/, "").replace(/\s*```$/, "");
    try {
      var parsed = JSON.parse(inner);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (e) {
      return null;
    }
  }

  function field(term, value) {
    if (!value) {
      return null;
    }
    var row = document.createElement("div");
    var label = document.createElement("strong");
    label.textContent = term + ": ";
    row.appendChild(label);
    // textContent, always. See the header of this file.
    row.appendChild(document.createTextNode(String(value)));
    return row;
  }

  function safeLink(url) {
    var text = String(url || "");
    var lowered = text.toLowerCase();
    var web = lowered.indexOf("https://") === 0 || lowered.indexOf("http://") === 0;
    if (!web) {
      // Shown, never linked. This is the guard that matters: an href the
      // suggester controls is the other way to run script on a page holding a
      // token, so anything that is not plainly the web stays inert text.
      return document.createTextNode(text + " (not a web address — will be rejected)");
    }
    var link = document.createElement("a");
    link.href = text;
    link.textContent = text + (lowered.indexOf("http://") === 0 ? " (http)" : "");
    link.rel = "noopener noreferrer";
    return link;
  }

  function render(issues) {
    var list = el("suggestions");
    list.textContent = "";
    if (!issues.length) {
      var empty = document.createElement("li");
      empty.textContent = "Nothing is waiting. ";
      list.appendChild(empty);
      say("No suggestions are waiting.");
      return;
    }
    issues.forEach(function (issue, index) {
      list.appendChild(card(issue, index, issues.length));
    });
    say(issues.length + (issues.length === 1 ? " suggestion" : " suggestions") + " waiting.");
  }

  function card(issue, index, total) {
    var item = document.createElement("li");
    var article = document.createElement("article");
    article.setAttribute("aria-labelledby", "issue-" + issue.number);
    article.tabIndex = -1;
    article.id = "card-" + issue.number;

    var heading = document.createElement("h3");
    heading.id = "issue-" + issue.number;
    heading.textContent = String(issue.title || "(no title)");
    article.appendChild(heading);

    var meta = document.createElement("p");
    meta.textContent =
      "Issue #" + issue.number + " — " + (index + 1) + " of " + total + ".";
    article.appendChild(meta);

    var pick = pickBlock(issue.body);
    if (!pick) {
      var warn = document.createElement("p");
      warn.textContent =
        "This issue has no readable pick block, so approving it would publish " +
        "nothing. Open it on GitHub and add one, or decline it.";
      article.appendChild(warn);
    } else {
      [
        ["Kind", pick.type],
        ["Name", pick.title],
        ["Description", pick.description],
        ["Language", pick.language],
        ["Group", pick.collection]
      ].forEach(function (pair) {
        var row = field(pair[0], pair[1]);
        if (row) {
          article.appendChild(row);
        }
      });
      var address = document.createElement("div");
      var addressLabel = document.createElement("strong");
      addressLabel.textContent = "Address: ";
      address.appendChild(addressLabel);
      address.appendChild(safeLink(pick.feed_url || pick.stream_url || ""));
      article.appendChild(address);
    }

    var source = document.createElement("p");
    var link = document.createElement("a");
    link.href = "https://github.com/" + REPO + "/issues/" + issue.number;
    link.textContent = "Read the whole issue on GitHub";
    link.rel = "noopener noreferrer";
    source.appendChild(link);
    article.appendChild(source);

    var actions = document.createElement("p");
    actions.appendChild(button("Approve", function () { decide(issue, APPROVED, "Approved"); }));
    actions.appendChild(button("Decline", function () { decide(issue, DECLINED, "Declined"); }));
    actions.appendChild(button("Needs info", function () { needsInfo(issue); }));
    article.appendChild(actions);

    item.appendChild(article);
    return item;
  }

  function button(label, handler) {
    var control = document.createElement("button");
    control.type = "button";
    control.textContent = label;
    control.addEventListener("click", handler);
    return control;
  }

  /* -- decisions ------------------------------------------------------------ */

  function decide(issue, label, past) {
    say("Working…");
    api("/issues/" + issue.number + "/labels", { method: "POST", body: { labels: [label] } })
      .then(function () {
        return api("/issues/" + issue.number, { method: "PATCH", body: { state: "closed" } });
      })
      .then(function () {
        return load(past + " " + String(issue.title || "") + ".");
      })
      .catch(function (error) {
        say("That did not work: " + error.message);
      });
  }

  function needsInfo(issue) {
    var note = window.prompt("What do you need to know?");
    if (!note) {
      return;
    }
    say("Working…");
    api("/issues/" + issue.number + "/comments", { method: "POST", body: { body: note } })
      .then(function () {
        say("Asked on #" + issue.number + ".");
      })
      .catch(function (error) {
        say("That did not work: " + error.message);
      });
  }

  function load(prefix) {
    say((prefix ? prefix + " " : "") + "Loading…");
    return api(
      "/issues?state=open&labels=" + encodeURIComponent(SUGGESTION) + "&per_page=100"
    )
      .then(function (issues) {
        var open = (issues || []).filter(function (issue) { return !issue.pull_request; });
        render(open);
        if (prefix) {
          // Focus the first remaining card so the keyboard does not land back
          // at the top of the page after every decision.
          var first = document.querySelector("#suggestions article");
          if (first) {
            first.focus();
          }
          say(
            prefix +
              " " +
              (open.length
                ? open.length + (open.length === 1 ? " remaining." : " remaining.")
                : "None remaining.")
          );
        }
      })
      .catch(function (error) {
        say("Could not load the suggestions: " + error.message);
      });
  }

  /* -- adding one yourself --------------------------------------------------- */

  function addPick(event) {
    event.preventDefault();
    var pick = {
      type: el("add-kind").value || "stream",
      title: el("add-title").value.trim(),
      url: el("add-url").value.trim(),
      description: el("add-description").value.trim(),
      language: el("add-language").value.trim(),
      collection: el("add-collection").value.trim()
    };
    var errors = [];
    if (!pick.title) { errors.push("Give it a name."); }
    if (
      pick.url.toLowerCase().indexOf("https://") !== 0 &&
      pick.url.toLowerCase().indexOf("http://") !== 0
    ) {
      errors.push("The address should start with https:// or http://.");
    }
    if (!pick.description) { errors.push("Add a description."); }

    var box = el("add-errors");
    box.textContent = "";
    if (errors.length) {
      var list = document.createElement("ul");
      errors.forEach(function (message) {
        var row = document.createElement("li");
        row.textContent = message;
        list.appendChild(row);
      });
      box.appendChild(list);
      box.focus();
      return;
    }

    var payload = { type: pick.type, title: pick.title, description: pick.description };
    if (pick.language) { payload.language = pick.language; }
    if (pick.collection) { payload.collection = pick.collection; }
    payload[pick.type === "podcast" ? "feed_url" : "stream_url"] = pick.url;

    var body = [
      "**" + pick.title + "** -- added from the review page.",
      "",
      "- Kind: " + pick.type,
      "- Address: " + pick.url,
      "- Description: " + pick.description,
      "",
      "```json pick",
      JSON.stringify(payload, null, 2),
      "```"
    ].join("\n");

    say("Adding…");
    api("/issues", {
      method: "POST",
      body: {
        title: "[Pick] " + (pick.type === "podcast" ? "Podcast" : "Station") + ": " + pick.title,
        body: body,
        labels: [APPROVED]
      }
    })
      .then(function (issue) {
        say("Added as issue #" + issue.number + ". It publishes on the next build.");
        el("add-form").reset();
      })
      .catch(function (error) {
        say("That did not work: " + error.message);
      });
  }

  /* -- wiring ---------------------------------------------------------------- */

  el("signin-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var value = el("token").value.trim();
    if (!value) {
      say("Paste a token first.");
      return;
    }
    signIn(value, el("remember").checked).catch(function (error) {
      say("Could not sign in: " + error.message);
    });
  });
  el("signout").addEventListener("click", signOut);
  el("refresh").addEventListener("click", function () { load(); });
  el("add-form").addEventListener("submit", addPick);

  var existing = loadToken();
  if (existing) {
    signIn(existing, false).catch(function () { signOut(); });
  }
})();
