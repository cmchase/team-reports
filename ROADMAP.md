# 🗺️ Project Roadmap

This roadmap outlines the planned evolution of **Team Reports** — expanding from automated summaries to deeper insights that support team productivity, flow, and growth.
All new features maintain the same **Markdown-only**, **configuration-driven**, and **API-integrated** design philosophy.

---

## ⚡ **Recent Progress Summary (October 2025)**

**Major infrastructure completed in Phase 2:**
- ✅ **Configuration Management** – Layered YAML system with validation and environment overrides
- ✅ **Feature Flag Infrastructure** – Per-metric flags wired across all report generators  
- ✅ **Active Configuration Display** – Hash-based config tracking with automatic secret redaction
- ✅ **Comprehensive Testing** – 146+ unit tests with CI-ready foundation

**Ready for implementation:** Flow and delivery metric calculations with feature-flag controlled rollout.

---

## 🚀 Phase 1 — Current Capabilities (✅ Implemented)

* **Individual Reports**

  * Weekly and quarterly **Jira** reports for team performance and activity.
  * Weekly and quarterly **GitHub** reports for repository and contributor insights.
* **Multi-Platform Integration**

  * Separate Jira and GitHub data sources with shared configuration and credentials.
* **Smart Categorization & Filters**

  * Component-, project-, and keyword-based ticket grouping.
  * Flexible date ranges and customizable status filters.
* **Rich Markdown Output**

  * Structured reports with tables, highlights, and contributor summaries.
* **Automation**

  * Shell script execution for fast report generation.
* **Extensible Architecture**

  * Modular utilities for configuration, date handling, and API access.

---

## 🔥 Phase 2 — Data-Driven Metrics (🚧 Implementation Ready)

### Flow Metrics (Jira)

* **Cycle Time** – Time from "In Progress" → "Done" with team median and p90 values.
* **Work In Progress (WIP)** – Current active tickets per engineer and team total.
* **Blocked Time** – Total time spent in Blocked or equivalent states.

### Delivery Metrics (GitHub)

* **PR Lead Time** – Duration from first commit → merge, with filtering for trivial PRs.
* **Review Depth** – Reviewers per PR, number of comments, and review-to-author mapping (bot exclusion supported).

### Data Quality & Guardrails

* Identify missing transition histories, unlinked PR↔Issue relationships, and API fetch gaps.
* Add **Pass/Warn/Fail badges** and optional `fail_on_error` flag.

### Testing & Quality Assurance ✅ **COMPLETED** 

* ✅ **Comprehensive test coverage** – 146+ unit tests across all utilities
* ✅ **Configuration testing** – Validation, merging, and environment override tests
* ✅ **Mock-resistant design** – Core functionality tested with minimal external dependencies
* ✅ **CI-ready foundation** – Test suite ready for continuous integration

### Configuration Centralization ✅ **COMPLETED**

* ✅ **Feature flags implemented** – All metrics have dedicated flags (`metrics.flow.cycle_time`, `metrics.delivery.pr_lead_time`, etc.)
* ✅ **YAML configuration system** – Layered config with defaults, user overrides, and environment variables
* ✅ **Configuration validation** – Schema validation with strict/non-strict modes  
* ✅ **Active config display** – Hash-based config tracking in report footers with secret redaction
* ✅ **Environment integration** – Structured `.env` mapping with automatic redaction

---

## 📈 Phase 3 — Insights & Coaching (Planned)

### Growth & Coaching Signals

Derived indicators to support performance coaching and 1:1 conversations:

* **Autonomy** – % of Jira tickets opened by the assignee.
* **Collaboration** – Reviews given vs. received per engineer.
* **Quality Focus** – % of PRs adding tests or documentation.
* **Rework Ratio** – % of commits editing files modified in the last 14 days.
* Reports only surface **noteworthy deviations** (beyond ±1 std. dev.) to reduce noise.

### Correlation & Analysis

* **PR Size vs. Cycle Time** – Compute correlation (Pearson r).
* Output a short interpretive insight line and simple ASCII scatter bins.
* Enable CSV export for further visualization.

### Gentle Nudges

* Light "nudge" alerts in weekly reports:

  * PRs waiting for review >48h.
  * Engineers with 0 merged PRs or 0 closed tickets in 10 days.
  * Consistent WIP over limit for 5+ days.
* Include JSON export (`nudges.json`) for optional Slack or dashboard integration.

---

## 📊 Phase 4 — Longitudinal Insights (Upcoming)

* **Quarterly Trendlines** – ASCII mini-sparklines showing week-over-week trends for:

  * Cycle Time
  * PR Lead Time
  * Review Depth
  * Rework Ratio
* **CSV Artifact Exports** – Output minimal datasets for dashboards:

  * `flow_cycle_time.csv`
  * `delivery_prs.csv`
  * `coaching_signals.csv`
* **Unified Combined Reports (Optional)** – Create a single weekly file merging Jira + GitHub summaries with aligned time ranges.

---

## 🧪 Phase 5 — Quality & Scalability (Future)

* **Testing Coverage** – Raise test coverage for new modules to ≥85%. (Optional)
* **Fixtures & Stability** – Add deterministic fixtures for Jira/GitHub APIs and date ranges.
* **Report Polish**

  * Normalize all Markdown table formats.
  * Add a concise **Glossary** section with metric definitions.
  * Use inline footnotes (†) linking metrics to glossary anchors.
* **Change Tracking**

  * Maintain short, imperative changelog entries.
  * Version report schema changes clearly in output headers.

---

## 💡 Phase 6 — Stretch Goals (Exploratory)

* **Jira↔GitHub Auto-Linking**

  * Match PRs and commits to Jira tickets by key in branch names, titles, or commit messages.
* **Scheduled Reporting**

  * Lightweight cron-based automation for weekly and quarterly report generation.
* **Slack / Teams Integration**

  * Post summarized Markdown sections directly into team channels.
* **Dashboard Layer**

  * Optional static-site dashboard rendering CSV data into trend charts.
* **Multi-Team Support**

  * Generate reports for multiple teams from a single configuration file.

---

## 🧭 Implementation Strategy

Each new capability will be developed as **incremental, self-contained commits**:

1. Implement metric or feature.
2. Add config flag and documentation.
3. Extend Markdown output and glossary.
4. Update tests and changelog.

---

## ✅ Priority Summary

| Category                            | Focus                                 | Priority  |
| ----------------------------------- | ------------------------------------- | --------- |
| **Unified Reports (Jira+GitHub)**   | Cross-platform correlation            | 🔥 High   |
| **Flow & Delivery Metrics**         | Jira/GitHub performance indicators    | 🔥 High   |
| **Coaching Signals**                | Growth-oriented insights              | 🔥 High   |
| **Trend Analysis & CSV Exports**    | Historical and external visualization | 🔧 Medium |
| **Slack/Dashboard Integrations**    | Quality-of-life enhancements          | 💡 Future |
| **Scheduling & Multi-Team Support** | Scalability improvements              | 💡 Future |

---

## ✨ Goal

Empower engineering leaders and teams to **see their progress, friction, and growth patterns**—all through a simple, private, Markdown-based reporting suite that turns Jira and GitHub data into meaningful, actionable insight.

---

## 🤝 Contributing to the Roadmap

Interested in implementing any of these features? Here's how to get started:

1. **Check existing issues** for related discussions
2. **Open a feature request** to discuss the approach
3. **Review the [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** for architecture details
4. **Start with the utilities package** - most enhancements can leverage existing infrastructure
5. **Follow existing patterns** for consistency with current codebase

For questions about roadmap priorities or implementation approaches, please open an issue with the `roadmap` label.
