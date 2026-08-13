/*
 * Splent Editor
 *
 * A compact rich text editor over contenteditable, bundled with the post
 * feature so products keep working offline. No CDN, no build step, no
 * external dependency.
 *
 * The toolbar and the editing surface live in the template (so every visible
 * string goes through the translation catalog) and stay hidden until this
 * script wires them. Without JavaScript the plain <textarea> is the field,
 * which is the whole progressive enhancement story.
 *
 * Storage contract. On submit the editing surface is serialized back into
 * the original <textarea> as clean semantic HTML (strong/em, h2/h3, lists,
 * blockquote, pre, links, images). Pasted markup passes a whitelist
 * sanitizer. Markup already stored on the post is left alone beyond b/i
 * normalization, so content imported from WordPress survives editing.
 */
(function () {
  "use strict";

  var BLOCK_CMDS = { h2: "h2", h3: "h3", quote: "blockquote", code: "pre" };

  /* Tags the paste sanitizer lets through. Anything else is unwrapped so
     its children survive, which turns Word and Google Docs exports into
     plain semantic HTML. */
  var PASTE_TAGS = {
    p: 1, h2: 1, h3: 1, h4: 1, h5: 1, h6: 1, ul: 1, ol: 1, li: 1,
    blockquote: 1, pre: 1, code: 1, a: 1, img: 1, strong: 1, em: 1,
    br: 1, hr: 1, figure: 1, figcaption: 1,
    table: 1, thead: 1, tbody: 1, tr: 1, th: 1, td: 1
  };
  var PASTE_ATTRS = { a: ["href"], img: ["src", "alt"] };

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function escapeAttr(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renameTag(el, name) {
    var out = el.ownerDocument.createElement(name);
    while (el.firstChild) out.appendChild(el.firstChild);
    el.parentNode.replaceChild(out, el);
    return out;
  }

  function unwrap(el) {
    var parent = el.parentNode;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    parent.removeChild(el);
  }

  /* Whitelist cleaning for pasted fragments. Aggressive on purpose; paste
     is where junk markup enters a document. */
  function sanitizePasted(root) {
    var nodes = Array.prototype.slice.call(root.querySelectorAll("*"));
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (!el.parentNode) continue;
      var tag = el.tagName.toLowerCase();
      if (tag === "script" || tag === "style" || tag === "meta" || tag === "link") {
        el.parentNode.removeChild(el);
        continue;
      }
      if (tag === "b") { el = renameTag(el, "strong"); tag = "strong"; }
      else if (tag === "i") { el = renameTag(el, "em"); tag = "em"; }
      else if (tag === "h1") { el = renameTag(el, "h2"); tag = "h2"; }
      if (!PASTE_TAGS[tag]) { unwrap(el); continue; }
      var keep = PASTE_ATTRS[tag] || [];
      var attrs = Array.prototype.slice.call(el.attributes);
      for (var j = 0; j < attrs.length; j++) {
        if (keep.indexOf(attrs[j].name.toLowerCase()) === -1) {
          el.removeAttribute(attrs[j].name);
        }
      }
      if (tag === "a" && /^\s*javascript:/i.test(el.getAttribute("href") || "")) {
        el.removeAttribute("href");
      }
    }
  }

  /* Conservative normalization for what gets stored. Posts imported from
     WordPress carry markup this editor never produced; destroying it on the
     first edit would be data loss. Only what execCommand emits by itself is
     rewritten: b/i become strong/em, attribute-less div/span wrappers go. */
  function normalizeStored(root) {
    var nodes = Array.prototype.slice.call(root.querySelectorAll("b, i, div, span"));
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (!el.parentNode) continue;
      var tag = el.tagName.toLowerCase();
      if (tag === "b") renameTag(el, "strong");
      else if (tag === "i") renameTag(el, "em");
      else if (el.attributes.length === 0) {
        if (tag === "div") renameTag(el, "p");
        else unwrap(el);
      }
    }
  }

  function serialize(area) {
    var scratch = area.ownerDocument.createElement("div");
    scratch.innerHTML = area.innerHTML;
    normalizeStored(scratch);
    var html = scratch.innerHTML;
    // An empty document is an empty string, not a leftover placeholder.
    if (/^\s*(<p>(\s|<br\s*\/?>)*<\/p>)?\s*$/i.test(html)) return "";
    return html;
  }

  function initEditor(wrapper) {
    var textarea = wrapper.querySelector("textarea");
    var shell = wrapper.querySelector(".splent-editor");
    if (!textarea || !shell) return;
    var toolbar = shell.querySelector(".splent-editor__toolbar");
    var area = shell.querySelector(".splent-editor__area");
    if (!toolbar || !area) return;

    var form = textarea.form;
    var dialog = document.querySelector("[data-editor-image-dialog]");
    var linkPrompt = wrapper.getAttribute("data-label-link-url") || "Link URL";
    var sourceMode = false;
    var savedRange = null;

    area.innerHTML = textarea.value;
    if (!area.innerHTML.replace(/\s+/g, "")) area.innerHTML = "<p><br></p>";
    textarea.hidden = true;
    textarea.classList.add("splent-editor__sourcearea");
    // Move the textarea inside the shell so the HTML source view sits under
    // the toolbar. It stays inside the same <form>, so nothing changes for
    // submission; without JavaScript it never moves and stays the field.
    shell.appendChild(textarea);
    shell.hidden = false;

    try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch (e) { /* older engines */ }
    try { document.execCommand("styleWithCSS", false, false); } catch (e) { /* older engines */ }

    function setActive(cmd, on) {
      var button = toolbar.querySelector('button[data-cmd="' + cmd + '"]');
      if (button) button.classList.toggle("is-active", !!on);
    }

    function safeState(command) {
      try { return document.queryCommandState(command); } catch (e) { return false; }
    }

    function selectionElement() {
      var sel = window.getSelection();
      var node = sel.rangeCount ? sel.anchorNode : null;
      if (!node || !area.contains(node)) return null;
      return node.nodeType === 3 ? node.parentNode : node;
    }

    function currentBlock() {
      var node = selectionElement();
      while (node && node !== area) {
        var tag = node.tagName ? node.tagName.toLowerCase() : "";
        if (tag === "h2" || tag === "h3" || tag === "blockquote" || tag === "pre") return tag;
        node = node.parentNode;
      }
      return node ? "p" : null;
    }

    function insideLink() {
      var node = selectionElement();
      while (node && node !== area) {
        if (node.tagName && node.tagName.toLowerCase() === "a") return true;
        node = node.parentNode;
      }
      return false;
    }

    function refreshState() {
      if (sourceMode) return;
      var block = currentBlock();
      setActive("bold", safeState("bold"));
      setActive("italic", safeState("italic"));
      setActive("ul", safeState("insertUnorderedList"));
      setActive("ol", safeState("insertOrderedList"));
      setActive("h2", block === "h2");
      setActive("h3", block === "h3");
      setActive("quote", block === "blockquote");
      setActive("code", block === "pre");
      setActive("link", insideLink());
    }

    function restoreSelection() {
      area.focus();
      if (!savedRange) return;
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
    }

    function toggleLink() {
      if (insideLink()) {
        document.execCommand("unlink");
        return;
      }
      var url = window.prompt(linkPrompt, "https://");
      if (!url || url === "https://") return;
      var sel = window.getSelection();
      if (!sel.rangeCount || sel.isCollapsed) {
        document.execCommand(
          "insertHTML", false,
          '<a href="' + escapeAttr(url) + '">' + escapeHtml(url) + "</a>"
        );
      } else {
        document.execCommand("createLink", false, url);
      }
    }

    function openImageDialog() {
      if (!dialog || typeof dialog.showModal !== "function") return;
      var checked = dialog.querySelector("input[type=radio]:checked");
      if (checked) checked.checked = false;
      dialog.showModal();
    }

    function insertCheckedImage() {
      var checked = dialog.querySelector("input[type=radio]:checked");
      dialog.close();
      if (!checked || !checked.value) return;
      var label = checked.closest ? checked.closest("label") : null;
      var thumb = label ? label.querySelector("img") : null;
      var alt = thumb ? (thumb.getAttribute("alt") || "") : "";
      restoreSelection();
      document.execCommand(
        "insertHTML", false,
        '<img src="' + escapeAttr(checked.value) + '" alt="' + escapeAttr(alt) + '">'
      );
    }

    function toggleSource() {
      if (!sourceMode) {
        textarea.value = serialize(area);
        area.hidden = true;
        textarea.hidden = false;
        sourceMode = true;
        textarea.focus();
      } else {
        area.innerHTML = textarea.value;
        textarea.hidden = true;
        area.hidden = false;
        sourceMode = false;
        area.focus();
      }
      var buttons = toolbar.querySelectorAll("button[data-cmd]");
      for (var i = 0; i < buttons.length; i++) {
        var button = buttons[i];
        var isToggle = button.getAttribute("data-cmd") === "html";
        button.disabled = sourceMode && !isToggle;
        if (isToggle) button.classList.toggle("is-active", sourceMode);
      }
    }

    function run(cmd) {
      if (cmd === "html") { toggleSource(); return; }
      if (sourceMode) return;
      area.focus();
      if (cmd === "bold" || cmd === "italic" || cmd === "undo" || cmd === "redo") {
        document.execCommand(cmd);
      } else if (cmd === "ul") {
        document.execCommand("insertUnorderedList");
      } else if (cmd === "ol") {
        document.execCommand("insertOrderedList");
      } else if (BLOCK_CMDS[cmd]) {
        var target = BLOCK_CMDS[cmd];
        var value = currentBlock() === target ? "p" : target;
        document.execCommand("formatBlock", false, "<" + value + ">");
      } else if (cmd === "link") {
        toggleLink();
      } else if (cmd === "image") {
        openImageDialog();
        return; // selection is restored when the dialog inserts
      }
      refreshState();
    }

    toolbar.addEventListener("mousedown", function (e) {
      // Keep the text selection alive while a toolbar button is clicked.
      e.preventDefault();
    });

    toolbar.addEventListener("click", function (e) {
      var target = e.target;
      while (target && target !== toolbar && !(target.tagName && target.tagName.toLowerCase() === "button")) {
        target = target.parentNode;
      }
      if (!target || target === toolbar) return;
      var cmd = target.getAttribute("data-cmd");
      if (cmd) run(cmd);
    });

    document.addEventListener("selectionchange", function () {
      if (sourceMode) return;
      var sel = window.getSelection();
      if (sel.rangeCount && area.contains(sel.anchorNode)) {
        savedRange = sel.getRangeAt(0).cloneRange();
        refreshState();
      }
    });

    area.addEventListener("paste", function (e) {
      var data = e.clipboardData;
      if (!data) return;
      e.preventDefault();
      var html = data.getData("text/html");
      if (html) {
        var scratch = document.createElement("div");
        scratch.innerHTML = html;
        sanitizePasted(scratch);
        document.execCommand("insertHTML", false, scratch.innerHTML);
      } else {
        var text = data.getData("text/plain");
        if (text) document.execCommand("insertText", false, text);
      }
    });

    if (dialog) {
      var insertButton = dialog.querySelector("[data-editor-image-insert]");
      var cancelButton = dialog.querySelector("[data-editor-image-cancel]");
      if (cancelButton) {
        cancelButton.addEventListener("click", function () { dialog.close(); });
      }
      if (insertButton) {
        insertButton.addEventListener("click", insertCheckedImage);
        dialog.addEventListener("dblclick", function (e) {
          var node = e.target;
          while (node && node !== dialog && !(node.classList && node.classList.contains("media-picker__item"))) {
            node = node.parentNode;
          }
          if (!node || node === dialog) return;
          var radio = node.querySelector("input[type=radio]");
          if (radio) { radio.checked = true; insertCheckedImage(); }
        });
      }
    }

    if (form) {
      form.addEventListener("submit", function () {
        if (!sourceMode) textarea.value = serialize(area);
      });
    }

    refreshState();
  }

  ready(function () {
    var wrappers = document.querySelectorAll("[data-splent-editor]");
    for (var i = 0; i < wrappers.length; i++) initEditor(wrappers[i]);
  });
})();
