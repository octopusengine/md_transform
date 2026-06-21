(function () {
  var colorMap = {
    red: "#d94f4f",
    orange: "#d97706",
    yellow: "#d6a900",
    green: "#45a66a",
    blue: "#4f8cc9",
    purple: "#8b5cf6",
    pink: "#db5aa0",
    cyan: "#0891b2"
  };

  function parseDateValue(value) {
    var text = String(value || "").trim();
    var match = text.match(/^(-?\d{1,6})(?:-(\d{1,2})(?:-(\d{1,2}))?)?/);

    if (!match) {
      return NaN;
    }

    var year = Number(match[1]);
    var month = match[2] ? Number(match[2]) : 1;
    var day = match[3] ? Number(match[3]) : 1;

    return year * 365.2425 + (month - 1) * 30.436875 + day;
  }

  function itemColor(color) {
    if (!color) {
      return colorMap.blue;
    }

    var normalized = String(color).replace(/^#/, "").toLowerCase();
    if (colorMap[normalized]) {
      return colorMap[normalized];
    }

    if (/^[0-9a-f]{3,8}$/.test(normalized)) {
      return "#" + normalized;
    }

    return colorMap.blue;
  }

  function dateRangeLabel(item) {
    if (item.end) {
      return item.start + " - " + item.end;
    }

    return item.start;
  }

  function tooltipText(item) {
    var parts = [dateRangeLabel(item)];

    if (item.group) {
      parts.push(item.group);
    }

    if (item.content) {
      parts.push(item.content);
    }

    if (item.description) {
      parts.push(item.description);
    }

    return parts.join(" | ");
  }

  function createTextElement(tagName, className, text) {
    var element = document.createElement(tagName);
    element.className = className;
    element.textContent = text || "";
    return element;
  }

  function percent(value, min, span) {
    if (!isFinite(value) || !isFinite(min) || !isFinite(span) || span <= 0) {
      return 0;
    }

    return Math.max(0, Math.min(100, ((value - min) / span) * 100));
  }

  function normalizedItems(items) {
    return items
      .map(function (item) {
        var startValue = parseDateValue(item.start);
        var endValue = item.end ? parseDateValue(item.end) : startValue;

        return Object.assign({}, item, {
          startValue: startValue,
          endValue: isFinite(endValue) ? endValue : startValue
        });
      })
      .filter(function (item) {
        return isFinite(item.startValue);
      })
      .sort(function (a, b) {
        return a.startValue - b.startValue || a.endValue - b.endValue;
      });
  }

  function renderEmpty(output, message) {
    output.textContent = "";
    output.appendChild(createTextElement("div", "chronos-empty", message));
  }

  function renderTimeline(block, payload) {
    var output = block.querySelector(".chronos-output");
    var items = normalizedItems((payload && payload.items) || []);

    if (!output) {
      return;
    }

    if (!items.length) {
      renderEmpty(output, "No Chronos items recognized.");
      return;
    }

    var min = Math.min.apply(null, items.map(function (item) { return item.startValue; }));
    var max = Math.max.apply(null, items.map(function (item) { return item.endValue; }));
    var span = max - min;

    if (span <= 0) {
      span = 365.2425;
      min -= span / 2;
      max += span / 2;
    }

    output.textContent = "";

    var chart = document.createElement("div");
    chart.className = "chronos-chart";

    var axis = document.createElement("div");
    axis.className = "chronos-axis";
    chart.appendChild(axis);

    var axisLabels = document.createElement("div");
    axisLabels.className = "chronos-axis-labels";
    axisLabels.appendChild(createTextElement("span", "", items[0].start));
    axisLabels.appendChild(createTextElement("span", "", items[items.length - 1].end || items[items.length - 1].start));
    chart.appendChild(axisLabels);

    items.forEach(function (item) {
      var row = document.createElement("div");
      row.className = "chronos-row chronos-row-" + item.type;

      var meta = document.createElement("div");
      meta.className = "chronos-row-meta";
      meta.appendChild(createTextElement("span", "chronos-row-date", dateRangeLabel(item)));

      if (item.group) {
        meta.appendChild(createTextElement("span", "chronos-row-group", item.group));
      }

      var track = document.createElement("div");
      track.className = "chronos-row-track";

      var visual = document.createElement("div");
      visual.className = "chronos-item chronos-item-" + item.type;
      visual.title = tooltipText(item);
      visual.style.setProperty("--chronos-item-color", itemColor(item.color));
      visual.style.left = percent(item.startValue, min, span) + "%";

      if (item.end && item.type !== "point" && item.type !== "marker") {
        visual.classList.add("chronos-item-range");
        visual.style.width = Math.max(2, percent(item.endValue, min, span) - percent(item.startValue, min, span)) + "%";
      }

      var label = createTextElement("span", "chronos-item-label", item.content || dateRangeLabel(item));
      visual.appendChild(label);
      track.appendChild(visual);
      row.appendChild(meta);
      row.appendChild(track);
      chart.appendChild(row);
    });

    output.appendChild(chart);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".chronos-block").forEach(function (block) {
      var data = block.querySelector(".chronos-data");
      var payload = {};

      if (data) {
        try {
          payload = JSON.parse(data.textContent);
        } catch (error) {
          renderEmpty(block.querySelector(".chronos-output"), "Chronos data could not be read.");
          return;
        }
      }

      renderTimeline(block, payload);
    });
  });
})();
