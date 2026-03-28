// Collected Company - Search JavaScript with SSE support

class CardSearcher {
  constructor() {
    this.results = [];
    this.storesCompleted = 0;
    this.totalStores = 0;
    this.eventSource = null;
    this.defaultCardImage = null;
    // Track which store/locations are checked (all on by default)
    this.activeFilters = new Set();
    this.allFilters = new Set();
  }

  async search(cardName) {
    // Clear previous results
    this.results = [];
    this.storesCompleted = 0;
    this.activeFilters.clear();
    this.allFilters.clear();
    this.hideError();
    this.showLoadingState();
    document.getElementById("main-content").classList.add("hidden");
    document.getElementById("store-filters").innerHTML = "";

    // Close any existing connection
    if (this.eventSource) {
      this.eventSource.close();
    }

    // Connect to SSE endpoint
    this.eventSource = new EventSource(
      `/api/cards/search/stream?q=${encodeURIComponent(cardName)}`
    );

    this.eventSource.addEventListener("metadata", (e) => {
      const data = JSON.parse(e.data);
      this.totalStores = data.total_stores;
      this.renderCardHeader(data);
      this.updateProgress(0, this.totalStores);
    });

    this.eventSource.addEventListener("result", (e) => {
      const result = JSON.parse(e.data);
      this.addResult(result);
      this.renderFilters();
      this.renderResults();
    });

    this.eventSource.addEventListener("error", (e) => {
      const error = JSON.parse(e.data);
      console.warn("Store error:", error);
    });

    this.eventSource.addEventListener("progress", (e) => {
      const { completed, total } = JSON.parse(e.data);
      this.storesCompleted = completed;
      this.updateProgress(completed, total);
    });

    this.eventSource.addEventListener("complete", (e) => {
      this.hideLoadingState();
      this.showCompletionMessage();
      this.eventSource.close();
    });

    this.eventSource.onerror = (err) => {
      console.error("SSE error:", err);
      this.eventSource.close();
      this.showError("Connection lost. Please try again.");
      this.hideLoadingState();
    };
  }

  // Build a unique filter key for each store+location combo
  _filterKey(result) {
    const loc = result.location || "";
    return `${result.store_name}||${loc}`;
  }

  _filterLabel(key) {
    const [store, loc] = key.split("||");
    return loc ? `${store} - ${loc}` : store;
  }

  addResult(result) {
    this.results.push(result);
    const key = this._filterKey(result);
    this.allFilters.add(key);
    this.activeFilters.add(key);
    this.sortResults();
  }

  getFilteredResults() {
    return this.results.filter((r) => this.activeFilters.has(this._filterKey(r)));
  }

  sortResults() {
    const sortBy = document.getElementById("sort-select")?.value || "price";

    this.results.sort((a, b) => {
      switch (sortBy) {
        case "price":
          if (a.price === null) return 1;
          if (b.price === null) return -1;
          return a.price - b.price;
        case "price-desc":
          if (a.price === null) return 1;
          if (b.price === null) return -1;
          return b.price - a.price;
        case "store":
          return a.store_name.localeCompare(b.store_name);
        case "condition":
          return a.condition.localeCompare(b.condition);
        default:
          return 0;
      }
    });
  }

  renderFilters() {
    const container = document.getElementById("store-filters");

    // Group filters by store name
    const storeGroups = {};
    for (const key of this.allFilters) {
      const [store, loc] = key.split("||");
      if (!storeGroups[store]) storeGroups[store] = [];
      if (loc) storeGroups[store].push({ key, loc });
      else storeGroups[store].push({ key, loc: null });
    }

    container.innerHTML = "";

    for (const [store, locations] of Object.entries(storeGroups).sort()) {
      const group = document.createElement("div");
      group.className = "mb-2";

      if (locations.length === 1 && !locations[0].loc) {
        // Single-location store: just one checkbox
        const key = locations[0].key;
        group.appendChild(this._createCheckbox(key, store, "font-medium text-sm"));
      } else {
        // Multi-location store: store header + indented location checkboxes
        const header = document.createElement("div");
        header.className = "font-medium text-sm text-gray-200 mb-1";
        header.textContent = store;
        group.appendChild(header);

        const locList = document.createElement("div");
        locList.className = "ml-4 space-y-0.5";
        for (const { key, loc } of locations.sort((a, b) => (a.loc || "").localeCompare(b.loc || ""))) {
          locList.appendChild(this._createCheckbox(key, loc || store, "text-sm"));
        }
        group.appendChild(locList);
      }

      container.appendChild(group);
    }
  }

  _createCheckbox(filterKey, label, className) {
    const wrapper = document.createElement("label");
    wrapper.className = `flex items-center gap-2 cursor-pointer ${className} text-gray-300 hover:text-gray-100`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = this.activeFilters.has(filterKey);
    checkbox.className = "rounded bg-gray-700 border-gray-500 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800";
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        this.activeFilters.add(filterKey);
      } else {
        this.activeFilters.delete(filterKey);
      }
      this.renderResults();
    });

    const text = document.createElement("span");
    text.textContent = label;

    wrapper.appendChild(checkbox);
    wrapper.appendChild(text);
    return wrapper;
  }

  renderCardHeader(data) {
    const cardHeader = document.getElementById("card-header");
    const cardName = document.getElementById("card-name");
    const cardImage = document.getElementById("card-image");
    const cardLink = document.getElementById("card-scryfall-link");

    cardName.textContent = data.card_name;

    if (data.card_image_url) {
      cardImage.src = data.card_image_url;
      cardImage.alt = data.card_name;
      cardImage.classList.remove("hidden");
      this.defaultCardImage = data.card_image_url;
    } else {
      cardImage.classList.add("hidden");
      this.defaultCardImage = null;
    }

    if (data.scryfall_url) {
      cardLink.href = data.scryfall_url;
      cardLink.classList.remove("hidden");
    } else {
      cardLink.classList.add("hidden");
    }

    cardHeader.classList.remove("hidden");
  }

  renderResults() {
    const tbody = document.getElementById("results-tbody");
    const mainContent = document.getElementById("main-content");

    mainContent.classList.remove("hidden");

    const filtered = this.getFilteredResults();

    // Update filter count
    const filterCount = document.getElementById("filter-count");
    if (filtered.length < this.results.length) {
      filterCount.textContent = `Showing ${filtered.length} of ${this.results.length} results`;
    } else {
      filterCount.textContent = "";
    }

    // Track if this is a new result for animation
    const previousCount = tbody.children.length;

    // Clear and re-render
    tbody.innerHTML = "";

    filtered.forEach((result, index) => {
      const row = this.createResultRow(result, index >= previousCount);
      tbody.appendChild(row);
    });
  }

  createResultRow(result, isNew) {
    const row = document.createElement("tr");
    row.className = "hover:bg-gray-700/50 transition-colors";

    if (isNew) {
      row.classList.add("new-result-highlight");
    }

    // Hover: swap card preview image to this result's set-specific image
    if (result.product_image_url) {
      row.addEventListener("mouseenter", () => {
        const img = document.getElementById("card-image");
        if (img) img.src = result.product_image_url;
      });
      row.addEventListener("mouseleave", () => {
        const img = document.getElementById("card-image");
        if (img && this.defaultCardImage) img.src = this.defaultCardImage;
      });
    }

    // Store name + location
    const storeCell = document.createElement("td");
    storeCell.className = "px-6 py-4 whitespace-nowrap";
    const storeLink = document.createElement("a");
    storeLink.href = result.store_url;
    storeLink.target = "_blank";
    storeLink.className = "text-blue-400 hover:underline font-medium";
    storeLink.textContent = result.store_name;
    storeCell.appendChild(storeLink);
    if (result.location) {
      const locSpan = document.createElement("div");
      locSpan.className = "text-xs text-gray-400";
      locSpan.textContent = result.location;
      storeCell.appendChild(locSpan);
    }

    // Set
    const setCell = document.createElement("td");
    setCell.className = "px-6 py-4 text-sm text-gray-300";
    setCell.textContent = result.set_name || "-";

    // Price
    const priceCell = document.createElement("td");
    priceCell.className = "px-6 py-4 whitespace-nowrap font-bold text-gray-100";
    priceCell.textContent =
      result.price !== null ? `$${result.price.toFixed(2)}` : "-";

    // Condition
    const conditionCell = document.createElement("td");
    conditionCell.className = "px-6 py-4 whitespace-nowrap text-gray-300";
    conditionCell.textContent = result.condition || "-";

    // Foil
    const foilCell = document.createElement("td");
    foilCell.className = "px-6 py-4 whitespace-nowrap text-gray-300";
    foilCell.textContent = result.foil ? "Yes" : "No";

    // Stock
    const stockCell = document.createElement("td");
    stockCell.className = "px-6 py-4 whitespace-nowrap";
    if (result.stock_quantity > 0) {
      stockCell.textContent = result.stock_quantity;
      stockCell.classList.add("text-green-400");
    } else if (result.stock_quantity === 0) {
      stockCell.textContent = "Out";
      stockCell.classList.add("text-red-400");
    } else {
      stockCell.textContent = "-";
      stockCell.classList.add("text-gray-500");
    }

    // Link
    const linkCell = document.createElement("td");
    linkCell.className = "px-6 py-4 whitespace-nowrap";
    if (result.product_url) {
      const link = document.createElement("a");
      link.href = result.product_url;
      link.target = "_blank";
      link.className = "text-blue-400 hover:underline";
      link.textContent = "View";
      linkCell.appendChild(link);
    } else {
      linkCell.textContent = "-";
      linkCell.classList.add("text-gray-500");
    }

    row.appendChild(storeCell);
    row.appendChild(setCell);
    row.appendChild(priceCell);
    row.appendChild(conditionCell);
    row.appendChild(foilCell);
    row.appendChild(stockCell);
    row.appendChild(linkCell);

    return row;
  }

  updateProgress(completed, total) {
    const percentage = (completed / total) * 100;
    const progressBar = document.getElementById("progress-bar");
    const progressText = document.getElementById("progress-text");

    progressBar.style.width = `${percentage}%`;
    progressText.textContent = `Searching ${total} stores... ${completed}/${total}`;
  }

  showLoadingState() {
    document.getElementById("loading-container").classList.remove("hidden");
    document.getElementById("completion-message").classList.add("hidden");
  }

  hideLoadingState() {
    document.getElementById("loading-container").classList.add("hidden");
  }

  showCompletionMessage() {
    const filtered = this.getFilteredResults();
    const message = `Found ${this.results.length} result${
      this.results.length !== 1 ? "s" : ""
    } from ${this.storesCompleted} stores`;
    const elem = document.getElementById("completion-message");
    elem.textContent = message;
    elem.classList.remove("hidden");
  }

  showError(message) {
    const container = document.getElementById("error-container");
    const messageElem = document.getElementById("error-message");
    messageElem.textContent = message;
    container.classList.remove("hidden");
  }

  hideError() {
    document.getElementById("error-container").classList.add("hidden");
  }
}

// Initialize searcher
const searcher = new CardSearcher();

// Handle form submission
document.getElementById("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const query = document.getElementById("card-search").value;
  if (query.trim()) {
    searcher.search(query.trim());
  }
});

// Handle sort change
document.getElementById("sort-select")?.addEventListener("change", () => {
  searcher.sortResults();
  searcher.renderResults();
});
