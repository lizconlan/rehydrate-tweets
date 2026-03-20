const ArchiveViewer = (() => {
  const state = {
    manifest: [],
    selectedId: null,
    query: "",
    activeFilter: "all",
    account: "",
    dateFrom: "",
    dateTo: "",
  };
  const FILTERS = [
    { id: "all", label: "All", predicate: () => true },
    { id: "media", label: "Media", predicate: (tweet) => (tweet.media_count || 0) > 0 },
    { id: "video", label: "Video", predicate: (tweet) => Boolean(tweet.has_video) },
    { id: "managed", label: "Imported", predicate: (tweet) => tweet.source_kind === "managed" },
  ];

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function localAssetPath(assetPath) {
    if (!assetPath) {
      return "";
    }

    if (/^https?:\/\//.test(assetPath)) {
      return assetPath;
    }

    return `downloads/${assetPath.replace(/^\/+/, "")}`;
  }

  function sourceCandidates(item, kind) {
    const candidates = [];

    if (kind === "avatar") {
      if (item.profile_image_s3) {
        candidates.push(localAssetPath(item.profile_image_s3));
      }
      if (item.profile_image_url) {
        candidates.push(item.profile_image_url);
      }
      return candidates.filter(Boolean);
    }

    if (item.s3_url) {
      if (item.s3_url.includes("/")) {
        candidates.push(localAssetPath(item.s3_url));
      } else {
        candidates.push(localAssetPath(`liked_media/${item.s3_url}`));
        candidates.push(localAssetPath(item.s3_url));
      }
    }

    if (item.url) {
      candidates.push(item.url);
    }

    return candidates.filter(Boolean);
  }

  function encodedFallbacks(candidates) {
    return escapeHtml(JSON.stringify(candidates.slice(1)));
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) {
      return "";
    }

    const parsed = new Date(timestamp);
    if (Number.isNaN(parsed.getTime())) {
      return timestamp;
    }

    return parsed.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  function formatShortDate(timestamp) {
    if (!timestamp) {
      return "";
    }

    const parsed = new Date(timestamp);
    if (Number.isNaN(parsed.getTime())) {
      return timestamp;
    }

    return parsed.toLocaleDateString(undefined, {
      dateStyle: "medium",
    });
  }

  function currentFilter() {
    return FILTERS.find((filter) => filter.id === state.activeFilter) || FILTERS[0];
  }

  function filteredTweets() {
    const normalized = state.query.trim().toLowerCase();
    const filter = currentFilter();

    return state.manifest.filter((tweet) => {
      if (!filter.predicate(tweet)) {
        return false;
      }

      if (!normalized) {
        // continue to structured filters
      } else {
        const haystack = [
          tweet.id,
          tweet.text,
          tweet.author?.username,
          tweet.author?.display_name,
        ]
          .join(" ")
          .toLowerCase();

        if (!haystack.includes(normalized)) {
          return false;
        }
      }

      if (state.account && tweet.author?.username !== state.account) {
        return false;
      }

      const tweetDate = (tweet.timestamp || "").slice(0, 10);
      if (state.dateFrom && tweetDate && tweetDate < state.dateFrom) {
        return false;
      }
      if (state.dateTo && tweetDate && tweetDate > state.dateTo) {
        return false;
      }

      return true;
    });
  }

  function populateAccountFilter() {
    const select = document.getElementById("account-filter");
    if (!select) {
      return;
    }

    const accounts = [...new Set(
      state.manifest
        .map((tweet) => tweet.author?.username)
        .filter(Boolean),
    )].sort((a, b) => a.localeCompare(b));

    select.innerHTML = [
      '<option value="">All accounts</option>',
      ...accounts.map((account) => `<option value="${escapeHtml(account)}">@${escapeHtml(account)}</option>`),
    ].join("");

    select.value = state.account;
  }

  function renderArchiveSummary() {
    const summary = document.getElementById("archive-summary");
    if (!summary) {
      return;
    }

    const total = state.manifest.length;
    const withMedia = state.manifest.filter((tweet) => (tweet.media_count || 0) > 0).length;
    const withVideo = state.manifest.filter((tweet) => tweet.has_video).length;
    const imported = state.manifest.filter((tweet) => tweet.source_kind === "managed").length;

    summary.innerHTML = `
      <div class="summary-card">
        <span class="summary-value">${total}</span>
        <span class="summary-label">Loaded</span>
      </div>
      <div class="summary-card">
        <span class="summary-value">${withMedia}</span>
        <span class="summary-label">With media</span>
      </div>
      <div class="summary-card">
        <span class="summary-value">${withVideo}</span>
        <span class="summary-label">Video</span>
      </div>
      <div class="summary-card">
        <span class="summary-value">${imported}</span>
        <span class="summary-label">Imported</span>
      </div>
    `;
  }

  function renderFilterChips() {
    const host = document.getElementById("filter-chips");
    if (!host) {
      return;
    }

    host.innerHTML = FILTERS.map((filter) => `
      <button
        class="filter-chip ${filter.id === state.activeFilter ? "is-active" : ""}"
        data-filter-id="${filter.id}"
        type="button"
      >
        ${escapeHtml(filter.label)}
      </button>
    `).join("");

    host.querySelectorAll(".filter-chip").forEach((button) => {
      button.addEventListener("click", () => {
        state.activeFilter = button.dataset.filterId;
        applyFilters();
      });
    });
  }

  function renderResultsMeta(tweets) {
    const meta = document.getElementById("results-meta");
    if (!meta) {
      return;
    }

    const filterLabel = currentFilter().label;
    const selectionDate = tweets[0] ? formatShortDate(tweets[0].timestamp) : "";
    const accountLabel = state.account ? ` · @${state.account}` : "";
    const dateLabel = state.dateFrom || state.dateTo
      ? ` · ${state.dateFrom || "start"} to ${state.dateTo || "now"}`
      : "";
    meta.textContent = tweets.length
      ? `${tweets.length} ${filterLabel.toLowerCase()} result${tweets.length === 1 ? "" : "s"}${accountLabel}${dateLabel}${selectionDate ? ` · newest ${selectionDate}` : ""}`
      : "No tweets match the current filters";
  }

  function renderMedia(media = []) {
    if (!media.length) {
      return "";
    }

    const items = media
      .map((item) => {
        const candidates = sourceCandidates(item, "media");
        const src = candidates[0];
        const alt = escapeHtml(item.alt_text || item.type || "Tweet media");

        if (!src) {
          return "";
        }

        if (item.type === "video") {
          return `
            <figure class="media-card">
              <video class="media-video" controls playsinline preload="metadata" data-current-src="${escapeHtml(src)}" data-fallbacks="${encodedFallbacks(candidates)}">
                <source src="${escapeHtml(src)}" type="video/mp4">
                Your browser could not play this local video file.
              </video>
              <figcaption class="media-caption">
                <a href="${escapeHtml(item.url || src)}" target="_blank" rel="noreferrer">Open video source</a>
              </figcaption>
            </figure>
          `;
        }

        return `
          <figure class="media-card">
            <img class="media-image" src="${escapeHtml(src)}" alt="${alt}" data-fallbacks="${encodedFallbacks(candidates)}">
          </figure>
        `;
      })
      .join("");

    return `<section class="media-grid">${items}</section>`;
  }

  function renderLinks(links = []) {
    if (!links.length) {
      return "";
    }

    const items = links
      .map((link) => {
        const label = link.title || link.display_url || link.expanded_url;
        return `
          <li>
            <a href="${escapeHtml(link.expanded_url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>
          </li>
        `;
      })
      .join("");

    return `
      <section class="meta-block">
        <h3>Links</h3>
        <ul class="meta-list">${items}</ul>
      </section>
    `;
  }

  function renderMentions(mentions = []) {
    if (!mentions.length) {
      return "";
    }

    const items = mentions
      .map((mention) => `<li>@${escapeHtml(mention.user_name)}</li>`)
      .join("");

    return `
      <section class="meta-block">
        <h3>Mentions</h3>
        <ul class="meta-list">${items}</ul>
      </section>
    `;
  }

  function renderTweet(tweet) {
    const author = tweet.author || {};
    const avatarCandidates = sourceCandidates(author, "avatar");
    const avatarSrc = avatarCandidates[0];
    const profileUrl = author.username ? `https://twitter.com/${author.username}` : "#";
    const tweetUrl = tweet.direct_link || profileUrl;

    return `
      <article class="tweet-card">
        <header class="tweet-header">
          <a class="author-link" href="${escapeHtml(profileUrl)}" target="_blank" rel="noreferrer">
            ${avatarSrc ? `<img class="author-avatar" src="${escapeHtml(avatarSrc)}" alt="" data-fallbacks="${encodedFallbacks(avatarCandidates)}">` : '<div class="author-avatar author-avatar--placeholder"></div>'}
            <div class="author-copy">
              <div class="author-name-row">
                <strong>${escapeHtml(author.display_name || author.username || "Unknown author")}</strong>
                ${author.verified ? '<span class="verified-badge">Verified</span>' : ""}
              </div>
              <div class="author-handle">@${escapeHtml(author.username || "unknown")}</div>
            </div>
          </a>
          <a class="tweet-link" href="${escapeHtml(tweetUrl)}" target="_blank" rel="noreferrer">Open original</a>
        </header>
        <div class="tweet-body">
          <p class="tweet-text">${escapeHtml(tweet.text || "").replace(/\n/g, "<br>")}</p>
          ${renderMedia(tweet.media)}
        </div>
        <footer class="tweet-footer">
          <span>${escapeHtml(formatTimestamp(tweet.timestamp))}</span>
          <span>${(tweet.media || []).length} media item${(tweet.media || []).length === 1 ? "" : "s"}</span>
        </footer>
        <div class="tweet-meta">
          ${renderLinks(tweet.external_links)}
          ${renderMentions(tweet.mentions)}
        </div>
      </article>
    `;
  }

  async function fetchJson(path) {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`Unable to load ${path}`);
    }

    return response.json();
  }

  function setStatus(message) {
    document.querySelectorAll("[data-role='status']").forEach((node) => {
      node.textContent = message;
    });
  }

  function updateSelectionDetails(tweet) {
    const panel = document.getElementById("tweet-detail");
    if (!panel) {
      return;
    }

    panel.innerHTML = renderTweet(tweet);
    activateFallbacks(panel);
  }

  function nextFallback(node, applySource) {
    const fallbackList = JSON.parse(node.dataset.fallbacks || "[]");
    const next = fallbackList.shift();

    if (!next) {
      return;
    }

    node.dataset.fallbacks = JSON.stringify(fallbackList);
    applySource(next);
  }

  function activateFallbacks(scope) {
    scope.querySelectorAll("img[data-fallbacks]").forEach((node) => {
      node.addEventListener("error", () => {
        nextFallback(node, (next) => {
          node.src = next;
        });
      });
    });

    scope.querySelectorAll("video[data-fallbacks]").forEach((node) => {
      node.addEventListener("error", () => {
        nextFallback(node, (next) => {
          const source = node.querySelector("source");
          if (source) {
            source.src = next;
          } else {
            node.src = next;
          }
          node.dataset.currentSrc = next;
          node.load();
        });
      });
    });
  }

  function updateSelectedListItem() {
    document.querySelectorAll(".tweet-list-item").forEach((node) => {
      node.classList.toggle("is-selected", node.dataset.tweetId === state.selectedId);
    });
  }

  async function selectTweet(tweetId, pushHistory = true) {
    if (!tweetId) {
      return;
    }

    state.selectedId = tweetId;
    updateSelectedListItem();
    setStatus("Loading tweet...");

    try {
      const tweet = await fetchJson(`downloads/${tweetId}.json`);
      updateSelectionDetails(tweet);
      setStatus(`${state.manifest.length} archived tweets loaded`);

      if (pushHistory) {
        const url = new URL(window.location.href);
        url.searchParams.set("tweet_id", tweetId);
        window.history.replaceState({}, "", url);
      }
    } catch (error) {
      updateSelectionDetails({
        text: "This tweet JSON could not be loaded from the local viewer cache.",
        author: { username: "viewer", display_name: "Archive Viewer" },
        media: [],
        mentions: [],
        external_links: [],
      });
      setStatus(error.message);
    }
  }

  function renderList(tweets) {
    const list = document.getElementById("tweet-list");
    if (!list) {
      return;
    }

    if (!tweets.length) {
      list.innerHTML = '<li class="empty-state">No local hydrated tweets matched that search.</li>';
      return;
    }

    list.innerHTML = tweets
      .map((tweet) => {
        const byline = tweet.author?.display_name || tweet.author?.username || "Unknown author";
        const avatarCandidates = sourceCandidates(tweet.author || {}, "avatar");
        const avatarSrc = avatarCandidates[0];
        const timestampLabel = formatTimestamp(tweet.timestamp);
        const badges = [];
        if (tweet.source_kind === "managed") {
          badges.push('<span class="tweet-list-badge">Imported</span>');
        }
        if (tweet.has_video) {
          badges.push('<span class="tweet-list-badge">Video</span>');
        } else if ((tweet.media_count || 0) > 0) {
          badges.push(`<span class="tweet-list-badge">${tweet.media_count} media</span>`);
        }

        return `
          <li>
            <button class="tweet-list-item" data-tweet-id="${escapeHtml(tweet.id)}" type="button">
              <span class="tweet-list-row">
                ${avatarSrc ? `<img class="tweet-list-avatar" src="${escapeHtml(avatarSrc)}" alt="" data-fallbacks="${encodedFallbacks(avatarCandidates)}">` : '<span class="tweet-list-avatar tweet-list-avatar--placeholder"></span>'}
                <span class="tweet-list-content">
                  <span class="tweet-list-heading">
                    <span class="tweet-list-title-row">
                      <span class="tweet-list-title">${escapeHtml(byline)}</span>
                      <span class="tweet-list-handle">@${escapeHtml(tweet.author?.username || "unknown")}</span>
                      <span class="tweet-list-dot">·</span>
                      <span class="tweet-list-date">${escapeHtml(timestampLabel)}</span>
                    </span>
                    <span class="tweet-list-badges">${badges.join("")}</span>
                  </span>
                  <span class="tweet-list-preview">${escapeHtml(tweet.text_preview || tweet.text || "")}</span>
                </span>
              </span>
            </button>
          </li>
        `;
      })
      .join("");

    list.querySelectorAll(".tweet-list-item").forEach((button) => {
      button.addEventListener("click", () => selectTweet(button.dataset.tweetId));
    });

    updateSelectedListItem();
    activateFallbacks(list);
  }

  function applyFilter(query) {
    state.query = query;
    applyFilters();
  }

  function applyFilters() {
    const filtered = filteredTweets();
    renderList(filtered);
    renderFilterChips();
    renderResultsMeta(filtered);

    if (!filtered.some((tweet) => tweet.id === state.selectedId) && filtered[0]) {
      selectTweet(filtered[0].id, false);
    }
  }

  async function initArchivePage() {
    try {
      const manifestData = await fetchJson("downloads/index.json");
      state.manifest = manifestData.tweets || [];
      setStatus(`${state.manifest.length} archived tweets loaded`);
      renderArchiveSummary();
      populateAccountFilter();
      renderFilterChips();
      applyFilters();

      const filterInput = document.getElementById("tweet-filter");
      if (filterInput) {
        filterInput.addEventListener("input", (event) => applyFilter(event.target.value));
      }

      const accountFilter = document.getElementById("account-filter");
      if (accountFilter) {
        accountFilter.addEventListener("change", (event) => {
          state.account = event.target.value;
          applyFilters();
        });
      }

      const dateFrom = document.getElementById("date-from");
      if (dateFrom) {
        dateFrom.addEventListener("change", (event) => {
          state.dateFrom = event.target.value;
          applyFilters();
        });
      }

      const dateTo = document.getElementById("date-to");
      if (dateTo) {
        dateTo.addEventListener("change", (event) => {
          state.dateTo = event.target.value;
          applyFilters();
        });
      }

      const clearFilters = document.getElementById("clear-filters");
      if (clearFilters) {
        clearFilters.addEventListener("click", () => {
          state.query = "";
          state.account = "";
          state.dateFrom = "";
          state.dateTo = "";
          state.activeFilter = "all";
          document.getElementById("tweet-filter").value = "";
          document.getElementById("account-filter").value = "";
          document.getElementById("date-from").value = "";
          document.getElementById("date-to").value = "";
          applyFilters();
        });
      }

      const requestedId = getParam("tweet_id");
      const initialTweet = state.manifest.find((tweet) => tweet.id === requestedId) || state.manifest[0];
      if (initialTweet) {
        selectTweet(initialTweet.id, false);
      }
    } catch (error) {
      setStatus(error.message);
      renderList([]);
      updateSelectionDetails({
        text: "Run `make refresh-viewer-data` after adding some hydrated tweet JSON files.",
        author: { username: "viewer", display_name: "Archive Viewer" },
        media: [],
        mentions: [],
        external_links: [],
      });
    }
  }

  async function initSingleTweetPage() {
    const tweetId = getParam("tweet_id");
    const panel = document.getElementById("tweet-detail");
    if (!tweetId) {
      panel.innerHTML = renderTweet({
        text: "Add `?tweet_id=<id>` to the URL, or open the archive browser instead.",
        author: { username: "viewer", display_name: "Archive Viewer" },
        media: [],
        mentions: [],
        external_links: [],
      });
      setStatus("No tweet_id provided");
      return;
    }

    try {
      const tweet = await fetchJson(`downloads/${tweetId}.json`);
      panel.innerHTML = renderTweet(tweet);
      activateFallbacks(panel);
      setStatus(`Viewing tweet ${tweetId}`);
    } catch (error) {
      panel.innerHTML = renderTweet({
        text: `Could not load downloads/${tweetId}.json`,
        author: { username: "viewer", display_name: "Archive Viewer" },
        media: [],
        mentions: [],
        external_links: [],
      });
      setStatus(error.message);
    }
  }

  async function init() {
    const mode = document.body.dataset.mode || "archive";
    if (mode === "single") {
      await initSingleTweetPage();
      return;
    }

    await initArchivePage();
  }

  return { init };
})();

window.addEventListener("DOMContentLoaded", () => {
  ArchiveViewer.init();
});
