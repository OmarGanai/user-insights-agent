#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.slack import SlackWebhookClient
from config import Settings, get_chart_reference, get_chart_reference_catalog
from scripts.local_debug_pipeline import run_local_debug_pipeline


STAGE_FILENAMES = [
    "01_amplitude_query_charts.json",
    "02_typeform_feedback.json",
    "02b_typeform_feedback_themes.json",
    "02c_app_context_sections.json",
    "02d_ios_release_context.json",
    "03_ai_analysis.json",
    "04_slack_payload_preview.json",
]

BLOCK_KIT_BUILDER_URL = "https://app.slack.com/block-kit-builder/"

INDEX_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Pipeline Debug Studio</title>
  <style>
    @import url(\"https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap\");

    :root {
      --ink: #141414;
      --paper: #f5f2ea;
      --accent: #cf4b00;
      --accent-deep: #b43d00;
      --plum: #7b3f8b;
      --accent-soft: #ffede0;
      --card: #fffefb;
      --line: rgba(20, 20, 20, 0.15);
      --ok: #156f44;
      --warn: #8c3d00;
      --error: #7b001a;
      --pos: #156f44;
      --neg: #a02121;
      --neutral: #666;
      --radius: 16px;
      --shadow: 0 16px 40px rgba(0, 0, 0, 0.08);
      --slack-bg: #f8f6fa;
      --slack-line: #e7deef;
      --slack-text: #1d1c1d;
      --headline-font: \"Manrope\", \"Segoe UI\", sans-serif;
      --body-font: \"Manrope\", \"Segoe UI\", sans-serif;
      --mono-font: \"IBM Plex Mono\", monospace;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: var(--body-font);
      background:
        radial-gradient(circle at 20% 6%, #ffe9d6 0%, transparent 26%),
        radial-gradient(circle at 82% 10%, #f2e9fb 0%, transparent 22%),
        linear-gradient(180deg, #faf7f2 0%, #f2ede3 65%, #ebe5da 100%);
      padding: 28px 20px 40px;
    }

    .wrap {
      max-width: 1240px;
      margin: 0 auto;
    }

    .hero {
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      background: #fffaf4;
      padding: 26px 24px;
      position: relative;
      overflow: hidden;
    }

    .hero::after {
      content: \"\";
      position: absolute;
      right: -40px;
      top: -35px;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      border: 1px dashed rgba(207, 75, 0, 0.16);
      pointer-events: none;
    }

    .kicker {
      font-family: var(--mono-font);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(20, 20, 20, 0.65);
      margin-bottom: 8px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.04;
      font-family: var(--headline-font);
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    .hero p {
      margin: 0;
      max-width: 760px;
      color: rgba(20, 20, 20, 0.75);
      line-height: 1.5;
    }

    .grid {
      margin-top: 22px;
      display: grid;
      gap: 16px;
      grid-template-columns: 1fr;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card);
      box-shadow: var(--shadow);
      padding: 16px;
      min-width: 0;
    }

    .panel h2 {
      margin: 0 0 10px;
      font-family: var(--headline-font);
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.01em;
    }

    .run-controls-panel {
      position: relative;
      overflow: hidden;
    }

    .run-controls-panel::before {
      content: none;
    }

    .controls-details {
      border: 1px solid rgba(20, 20, 20, 0.12);
      border-radius: 12px;
      background: #fffdf9;
      overflow: hidden;
    }

    .controls-details summary {
      cursor: pointer;
      list-style: none;
      padding: 12px 14px;
      font-family: var(--headline-font);
      font-size: 17px;
      font-weight: 800;
      letter-spacing: -0.01em;
      background: #fff4ea;
      border-bottom: 1px solid rgba(20, 20, 20, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .controls-details summary::-webkit-details-marker {
      display: none;
    }

    .controls-details summary::after {
      content: "Show";
      font-family: var(--mono-font);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: rgba(20, 20, 20, 0.58);
    }

    .controls-details[open] summary::after {
      content: "Hide";
    }

    .controls-body {
      padding: 12px;
    }

    .field {
      margin-bottom: 12px;
    }

    .field label {
      display: block;
      margin-bottom: 5px;
      font-size: 13px;
      font-family: var(--body-font);
      font-weight: 700;
      color: rgba(20, 20, 20, 0.8);
    }

    .control-explainer {
      border: 1px solid rgba(20, 20, 20, 0.12);
      border-radius: 12px;
      background: #fff8ee;
      padding: 12px;
      margin-bottom: 12px;
      font-size: 13px;
      line-height: 1.45;
      color: rgba(20, 20, 20, 0.82);
    }

    .control-explainer strong {
      font-family: var(--mono-font);
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: rgba(20, 20, 20, 0.68);
      display: block;
      margin-bottom: 10px;
    }

    .control-flow {
      display: grid;
      gap: 8px;
    }

    .flow-item {
      display: grid;
      grid-template-columns: 26px 1fr;
      align-items: start;
      gap: 8px;
      padding: 8px 9px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(20, 20, 20, 0.08);
    }

    .flow-step {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      border: 1px solid rgba(20, 20, 20, 0.2);
      background: #fff;
      color: rgba(20, 20, 20, 0.8);
      font-family: var(--mono-font);
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
    }

    .flow-copy {
      font-size: 12px;
      color: rgba(20, 20, 20, 0.76);
      line-height: 1.35;
    }

    .flow-copy b {
      display: block;
      margin-bottom: 2px;
      color: rgba(20, 20, 20, 0.88);
      font-size: 13px;
    }

    .field-help {
      margin: 6px 0 0;
      font-size: 12px;
      color: rgba(20, 20, 20, 0.72);
      line-height: 1.45;
    }

    .field-help code {
      font-size: 11px;
    }

    .chart-guide {
      margin-top: 9px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
      padding: 9px;
    }

    .chart-guide-head {
      margin: 0 0 7px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-family: \"IBM Plex Mono\", monospace;
      color: rgba(20, 20, 20, 0.67);
    }

    .chart-guide-empty {
      margin: 0;
      font-size: 12px;
      color: rgba(20, 20, 20, 0.65);
      font-style: italic;
    }

    .chart-guide-note {
      margin: 0 0 7px;
      font-size: 12px;
      color: rgba(20, 20, 20, 0.74);
      border: 1px solid rgba(20, 20, 20, 0.14);
      border-radius: 8px;
      padding: 6px 8px;
      background: #fffaf4;
    }

    .chart-ref-wrap {
      border: 1px solid var(--line);
      border-radius: 9px;
      background: #fff;
      overflow-x: visible;
    }

    .chart-ref-table {
      width: 100%;
      border-collapse: collapse;
      min-width: 0;
      table-layout: fixed;
      font-size: 12px;
      font-family: \"IBM Plex Mono\", monospace;
    }

    .chart-ref-table th,
    .chart-ref-table td {
      padding: 7px 8px;
      border-bottom: 1px solid rgba(20, 20, 20, 0.08);
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .chart-ref-table th:nth-child(1),
    .chart-ref-table td:nth-child(1) { width: 14%; }
    .chart-ref-table th:nth-child(2),
    .chart-ref-table td:nth-child(2) { width: 27%; }
    .chart-ref-table th:nth-child(3),
    .chart-ref-table td:nth-child(3) { width: 16%; }
    .chart-ref-table th:nth-child(4),
    .chart-ref-table td:nth-child(4) { width: 31%; }
    .chart-ref-table th:nth-child(5),
    .chart-ref-table td:nth-child(5) { width: 12%; }

    .chart-ref-table th {
      background: #fff8ee;
      color: rgba(20, 20, 20, 0.82);
      font-weight: 600;
    }

    .chart-ref-table tr:last-child td {
      border-bottom: none;
    }

    .chart-ref-link {
      color: var(--plum);
      text-decoration: none;
      display: inline-block;
      max-width: 100%;
    }

    .chart-ref-link:hover {
      text-decoration: underline;
    }

    .chart-ref-unknown {
      color: rgba(20, 20, 20, 0.58);
      font-style: italic;
    }

    .chart-contract-list {
      margin: 0;
      padding-left: 14px;
    }

    .chart-contract-list li {
      margin-bottom: 4px;
      line-height: 1.35;
    }

    input[type=\"text\"],
    input[type=\"number\"],
    textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 11px;
      font-size: 14px;
      background: #fff;
      color: var(--ink);
      font-family: var(--body-font);
      transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
    }

    textarea#chartIds,
    input#outputDir {
      font-family: var(--mono-font);
      font-size: 13px;
    }

    input[type=\"text\"]:focus,
    input[type=\"number\"]:focus,
    textarea:focus {
      outline: none;
      border-color: rgba(207, 75, 0, 0.58);
      box-shadow: 0 0 0 4px rgba(123, 63, 139, 0.15);
    }

    textarea {
      min-height: 68px;
      resize: vertical;
    }

    .inline {
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr 1fr;
    }

    .checks {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      padding: 6px 0 2px;
    }

    .check {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 12px;
      background: var(--paper);
      font-size: 13px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .check input {
      accent-color: var(--accent);
    }

    .run-cta {
      margin-bottom: 12px;
      display: grid;
      gap: 10px;
      justify-items: center;
    }

    .run-plate {
      position: relative;
      width: clamp(188px, 28vw, 270px);
      aspect-ratio: 1 / 1;
      padding: 14px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, #fbfafc 0%, #ece8ef 100%);
      box-shadow:
        inset 0 2px 5px rgba(255, 255, 255, 0.92),
        inset 0 -8px 14px rgba(94, 80, 116, 0.2),
        0 14px 22px rgba(46, 27, 66, 0.18);
    }

    .run-plate::before {
      content: "";
      position: absolute;
      inset: 9px;
      border-radius: 50%;
      border: 1px solid rgba(70, 53, 95, 0.16);
      pointer-events: none;
    }

    .run-plate::after {
      content: "";
      position: absolute;
      left: 24%;
      right: 24%;
      bottom: 9px;
      height: 10px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(121, 92, 157, 0.34) 0%, rgba(121, 92, 157, 0) 75%);
      opacity: 0.45;
      pointer-events: none;
    }

    button {
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: #fff7f2;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: transform 140ms ease, filter 140ms ease;
    }

    button:hover {
      transform: translateY(-1px);
      filter: brightness(0.95);
    }

    .run-btn {
      width: 100%;
      height: 100%;
      min-height: 0;
      padding: 0;
      border-radius: 50%;
      position: relative;
      overflow: hidden;
      background: linear-gradient(180deg, #ffa07f 0%, #fb8268 55%, #eb6f62 100%);
      box-shadow:
        inset 0 4px 8px rgba(255, 255, 255, 0.24),
        inset 0 -12px 14px rgba(143, 34, 49, 0.32),
        0 7px 0 #b84b58,
        0 14px 16px rgba(150, 60, 78, 0.28);
      transform: translateY(-2px);
      transition: transform 180ms ease, filter 180ms ease, box-shadow 180ms ease;
    }

    .run-btn::before {
      content: "Run Pipeline";
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      font-family: var(--headline-font);
      font-size: clamp(16px, 2.4vw, 24px);
      font-weight: 800;
      letter-spacing: 0.01em;
      color: #fff7f2;
      text-shadow: 0 2px 4px rgba(120, 26, 33, 0.36);
      pointer-events: none;
    }

    .run-btn:hover {
      transform: translateY(-2px);
      filter: brightness(1.02);
      box-shadow:
        inset 0 4px 8px rgba(255, 255, 255, 0.24),
        inset 0 -12px 14px rgba(143, 34, 49, 0.32),
        0 7px 0 #b84b58,
        0 14px 16px rgba(150, 60, 78, 0.28);
    }

    .run-btn:active {
      transform: translateY(3px);
      box-shadow:
        inset 0 2px 6px rgba(255, 255, 255, 0.18),
        inset 0 -6px 10px rgba(143, 34, 49, 0.36),
        0 2px 0 #b84b58,
        0 6px 10px rgba(150, 60, 78, 0.22);
    }

    .run-btn.running {
      transform: translateY(3px);
      filter: none;
      box-shadow:
        inset 0 2px 6px rgba(255, 255, 255, 0.18),
        inset 0 -6px 10px rgba(143, 34, 49, 0.36),
        0 2px 0 #b84b58,
        0 6px 10px rgba(150, 60, 78, 0.22);
    }

    .run-btn:disabled {
      opacity: 1;
    }

    .run-btn.running:disabled {
      cursor: progress;
    }

    button:disabled {
      cursor: not-allowed;
      transform: none;
      opacity: 0.65;
    }

    .status {
      font-size: 13px;
      font-family: var(--mono-font);
      color: rgba(20, 20, 20, 0.7);
      text-align: center;
    }

    .status.ok { color: var(--ok); }
    .status.warn { color: var(--warn); }
    .status.error { color: var(--error); }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 11px;
      background: #fff;
    }

    .card .label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-family: var(--mono-font);
      color: rgba(20, 20, 20, 0.62);
      margin-bottom: 5px;
    }

    .card .value {
      font-size: 18px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .view-toggle {
      margin: 8px 0 10px;
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px;
      background: #fffaf4;
    }

    .mode-btn {
      appearance: none;
      border: none;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      font-family: var(--mono-font);
      background: transparent;
      color: rgba(20, 20, 20, 0.72);
      cursor: pointer;
      font-weight: 600;
    }

    .mode-btn.active {
      background: var(--accent);
      color: #fffaf4;
    }

    .slack-preview {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      margin-bottom: 12px;
      overflow: hidden;
    }

    .slack-preview.hidden {
      display: none;
    }

    .slack-editor {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      margin-bottom: 12px;
      overflow: hidden;
    }

    .slack-editor-head {
      font-size: 12px;
      font-family: var(--mono-font);
      padding: 10px 12px;
      background: #efe9f6;
      border-bottom: 1px solid var(--line);
      color: rgba(20, 20, 20, 0.82);
    }

    .slack-editor-body {
      padding: 10px;
    }

    .slack-editor-help {
      margin: 0 0 10px;
      font-size: 12px;
      color: rgba(20, 20, 20, 0.76);
      line-height: 1.42;
    }

    .slack-editor-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 8px;
    }

    .slack-editor-link {
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      background: #fff7f0;
      color: #4c2b00;
      font-size: 12px;
      font-family: var(--mono-font);
      text-decoration: none;
      font-weight: 600;
    }

    .slack-editor-link:hover {
      text-decoration: underline;
    }

    .slack-editor-btn {
      padding: 8px 12px;
      font-size: 12px;
      font-family: var(--mono-font);
      font-weight: 700;
      border-radius: 999px;
    }

    .slack-editor-btn.secondary {
      background: #e7f0ff;
      color: #123d77;
    }

    #slackPayloadEditor {
      min-height: 260px;
      font-family: var(--mono-font);
      font-size: 12px;
      line-height: 1.42;
      background: #faf9fc;
    }

    .slack-post-status {
      margin-top: 8px;
      font-size: 12px;
      text-align: left;
    }

    .slack-preview-head {
      font-size: 12px;
      font-family: var(--mono-font);
      padding: 10px 12px;
      background: var(--accent-soft);
      border-bottom: 1px solid var(--line);
      color: rgba(20, 20, 20, 0.82);
    }

    .slack-shell {
      background: var(--slack-bg);
      border: 1px solid var(--slack-line);
      border-radius: 12px;
      margin: 10px;
      overflow: hidden;
    }

    .slack-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      font-family: var(--mono-font);
      color: #4a3f5c;
      padding: 8px 10px;
      background: #ece4f2;
      border-bottom: 1px solid #ddd2e8;
    }

    .slack-body {
      padding: 10px;
      color: var(--slack-text);
      font-size: 14px;
      line-height: 1.42;
    }

    .slack-fallback {
      padding: 8px 10px;
      border-radius: 8px;
      background: #fff;
      border: 1px solid var(--slack-line);
      margin-bottom: 10px;
    }

    .slack-block {
      background: #fff;
      border: 1px solid var(--slack-line);
      border-radius: 8px;
      padding: 9px 10px;
      margin-bottom: 8px;
    }

    .slack-header {
      font-weight: 700;
    }

    .slack-divider {
      height: 1px;
      background: #d8cfdf;
      margin: 8px 0;
    }

    .slack-block a {
      color: #1264a3;
      text-decoration: none;
    }

    .slack-block code {
      font-family: var(--mono-font);
      font-size: 12px;
      background: #f4f4f4;
      border-radius: 4px;
      padding: 1px 4px;
    }

    .stage-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fffcf7;
      margin-top: 9px;
      overflow: hidden;
      max-width: 100%;
    }

    .stage-card summary {
      cursor: pointer;
      list-style: none;
      padding: 11px 12px;
      font-size: 13px;
      font-family: var(--mono-font);
      background: var(--accent-soft);
      border-bottom: 1px solid rgba(20, 20, 20, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .stage-card summary::-webkit-details-marker {
      display: none;
    }

    .stage-title {
      font-weight: 600;
      color: rgba(20, 20, 20, 0.86);
    }

    .stage-chip {
      font-size: 11px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      border-radius: 999px;
      border: 1px solid rgba(20, 20, 20, 0.14);
      padding: 3px 7px;
      background: #fffaf4;
      color: rgba(20, 20, 20, 0.62);
      white-space: nowrap;
    }

    .stage-card.machine-card summary {
      background: #f2ecff;
      border-bottom-color: #d8cfee;
    }

    .stage-card.machine-card .stage-chip {
      background: #32284d;
      color: #f3efff;
      border-color: #32284d;
    }

    .human-block {
      padding: 10px 12px;
      font-size: 14px;
      line-height: 1.45;
      color: #111;
      background: #fff;
      border-top: 1px solid rgba(20, 20, 20, 0.12);
    }

    .human-subtitle {
      margin-top: 10px;
      margin-bottom: 6px;
      font-size: 12px;
      font-family: var(--mono-font);
      color: #191919;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .human-list {
      margin: 8px 0 10px 18px;
      padding: 0;
    }

    .human-list li {
      margin-bottom: 6px;
      color: #161616;
    }

    .mono-pill {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      margin-right: 6px;
      margin-bottom: 6px;
      font-family: var(--mono-font);
      font-size: 12px;
      background: #fffaf4;
    }

    .value.pos { color: var(--pos); }
    .value.neg { color: var(--neg); }
    .value.neutral { color: var(--neutral); }

    .empty-note {
      font-size: 13px;
      color: #3f3f3f;
      padding: 8px 0;
      font-style: italic;
    }

    .human-table-wrap {
      overflow-x: auto;
      border: 1px solid rgba(20, 20, 20, 0.22);
      border-radius: 10px;
      background: #fff;
      margin-top: 8px;
    }

    .human-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      min-width: 620px;
      font-family: var(--mono-font);
    }

    .human-table th,
    .human-table td {
      border-bottom: 1px solid rgba(20, 20, 20, 0.08);
      padding: 8px;
      text-align: left;
      vertical-align: top;
      color: #121212;
    }

    .human-table th {
      background: #f1ece4;
      font-weight: 600;
      color: #111;
    }

    .machine-pre {
      margin: 0;
      padding: 12px;
      max-height: 360px;
      overflow: auto;
      max-width: 100%;
      font-size: 12px;
      line-height: 1.38;
      background: #fff;
      font-family: var(--mono-font);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .stage-card.machine-card .machine-pre {
      background: #1f1c2a;
      color: #e6e1f2;
      border-top: 1px solid #3b3450;
      max-height: 460px;
      padding: 14px 16px;
      line-height: 1.44;
      font-size: 12px;
    }

    @media (max-width: 1100px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 760px) {
      .run-plate {
        width: clamp(170px, 54vw, 224px);
      }
      .run-btn {
        min-height: 0;
      }
      .inline {
        grid-template-columns: 1fr;
      }
      .summary-cards {
        grid-template-columns: 1fr;
      }
      .hero {
        padding: 20px;
      }
      .panel h2 {
        font-size: 18px;
      }
      .flow-item {
        grid-template-columns: 24px 1fr;
      }
      .flow-step {
        width: 24px;
        height: 24px;
      }
      .chart-ref-table th:nth-child(1),
      .chart-ref-table td:nth-child(1) { width: 20%; }
      .chart-ref-table th:nth-child(2),
      .chart-ref-table td:nth-child(2) { width: 28%; }
      .chart-ref-table th:nth-child(3),
      .chart-ref-table td:nth-child(3) { width: 16%; }
      .chart-ref-table th:nth-child(4),
      .chart-ref-table td:nth-child(4) { width: 24%; }
      .chart-ref-table th:nth-child(5),
      .chart-ref-table td:nth-child(5) { width: 12%; }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <div class=\"kicker\">Amplitude Insights Bot</div>
      <h1>Pipeline Debug Studio</h1>
      <p>Run the full local debug pipeline from your browser, switch between human and machine views for each stage, then review/edit the exact Slack payload JSON before posting.</p>
    </section>

    <section class=\"grid\">
      <div class=\"panel run-controls-panel\">
        <div class=\"run-cta\">
          <div id=\"runPlate\" class=\"run-plate\">
            <button id=\"runBtn\" class=\"run-btn\" type=\"button\" aria-label=\"run pipeline\" onclick=\"(function(){var s=document.getElementById('status');if(window.__runPipeline){window.__runPipeline();return;}if(s){s.textContent='Run handler unavailable. Reload the page and try again.';s.className='status error';}})()\"></button>
          </div>
          <span id=\"status\" class=\"status\">Ready.</span>
        </div>
        <details class=\"controls-details\" id=\"runControlsDetails\">
          <summary>Controls</summary>
          <div class=\"controls-body\">
            <div class=\"control-explainer\">
              <strong>How To Use This</strong>
              <div class=\"control-flow\">
                <div class=\"flow-item\">
                  <span class=\"flow-step\">1</span>
                  <div class=\"flow-copy\"><b>Select Charts</b>Choose chart IDs to query for this run.</div>
                </div>
                <div class=\"flow-item\">
                  <span class=\"flow-step\">2</span>
                  <div class=\"flow-copy\"><b>Set Feedback Window</b>Pick how many recent days of Typeform feedback to include.</div>
                </div>
                <div class=\"flow-item\">
                  <span class=\"flow-step\">3</span>
                  <div class=\"flow-copy\"><b>Choose Output Mode</b>Leave output blank to keep run history, or set a fixed folder to replace previous files.</div>
                </div>
              </div>
            </div>

            <div class=\"field\">
              <label for=\"chartIds\">Charts To Query (chart IDs, comma separated)</label>
              <textarea id=\"chartIds\" placeholder=\"oys29da5,rviqohkp\"></textarea>
              <p class=\"field-help\">Each chart ID maps to one Amplitude chart. Use the reference table below to confirm chart name, chart type, and metric contract alignment before running.</p>
              <div id=\"chartGuide\" class=\"chart-guide\">
                <p class=\"chart-guide-head\">Chart ID Reference</p>
                <p class=\"chart-guide-empty\">Add one or more chart IDs to preview chart names and links.</p>
              </div>
            </div>

            <div class=\"inline\">
              <div class=\"field\">
                <label for=\"lookback\">Feedback Lookback (days)</label>
                <input id=\"lookback\" type=\"number\" min=\"1\" value=\"7\" />
                <p class=\"field-help\">Lookback days means: include Typeform responses submitted in the last N days. Example: <code>7</code> includes the past 7 days of feedback in this run.</p>
              </div>
              <div class=\"field\">
                <label for=\"outputDir\">Output Directory</label>
                <input id=\"outputDir\" type=\"text\" placeholder=\"Leave blank for timestamped history (recommended)\" />
                <p class=\"field-help\">Leave blank to create a new timestamped folder (keeps historical runs). Set a fixed folder to overwrite files from the previous run in that same folder.</p>
              </div>
            </div>

            <div class=\"checks\">
              <label class=\"check\"><input id=\"skipAi\" type=\"checkbox\" /> Skip AI</label>
            </div>

          </div>
        </details>
      </div>

      <div class=\"panel\">
        <h2>Output</h2>
        <div id=\"summaryCards\" class=\"summary-cards\"></div>

        <div class=\"view-toggle\" role=\"tablist\" aria-label=\"View mode\">
          <button type=\"button\" class=\"mode-btn active\" data-mode=\"human\" role=\"tab\" aria-selected=\"true\" onclick=\"(function(){var s=document.getElementById('status');if(s){s.textContent='Inline human toggle click captured';s.className='status warn';}console.log('[PipelineDebugUI][inline] human toggle click');if(window.__setMode){window.__setMode('human');}else{console.error('[PipelineDebugUI][inline] window.__setMode missing');}})()\">Human Readable</button>
          <button type=\"button\" class=\"mode-btn\" data-mode=\"machine\" role=\"tab\" aria-selected=\"false\" onclick=\"(function(){var s=document.getElementById('status');if(s){s.textContent='Inline machine toggle click captured';s.className='status warn';}console.log('[PipelineDebugUI][inline] machine toggle click');if(window.__setMode){window.__setMode('machine');}else{console.error('[PipelineDebugUI][inline] window.__setMode missing');}})()\">Machine Readable</button>
        </div>
        <div id=\"slackPreview\" class=\"slack-preview\"></div>
        <div class=\"slack-editor\">
          <div class=\"slack-editor-head\">Slack Payload Source Of Truth (Exact JSON)</div>
          <div class=\"slack-editor-body\">
            <p class=\"slack-editor-help\">
              Slack preview above is a local approximation. For Block Kit-accurate rendering, paste this JSON into Block Kit Builder, then post this same edited payload from here.
            </p>
            <div class=\"slack-editor-actions\">
              <a id=\"openBlockKitBuilder\" class=\"slack-editor-link\" href=\"https://app.slack.com/block-kit-builder/\" target=\"_blank\" rel=\"noreferrer noopener\">Open Block Kit Builder</a>
              <a class=\"slack-editor-link\" href=\"https://docs.slack.dev/reference/block-kit/\" target=\"_blank\" rel=\"noreferrer noopener\">Block Kit Reference</a>
              <button id=\"copySlackPayloadBtn\" class=\"slack-editor-btn secondary\" type=\"button\">Copy Payload JSON</button>
              <button id=\"postSlackPayloadBtn\" class=\"slack-editor-btn\" type=\"button\">Post Edited Payload To Slack</button>
            </div>
            <textarea id=\"slackPayloadEditor\" spellcheck=\"false\" placeholder=\"Run pipeline to load Slack payload JSON\"></textarea>
            <div id=\"slackPostStatus\" class=\"status slack-post-status\">Run pipeline to load payload.</div>
          </div>
        </div>
        <div id=\"stageResults\"></div>
      </div>
    </section>
  </div>

  <script>
    (() => {
    const UI_LOG_PREFIX = "[PipelineDebugUI]";
    const uiLog = (...args) => console.log(UI_LOG_PREFIX, ...args);
    const uiWarn = (...args) => console.warn(UI_LOG_PREFIX, ...args);
    const uiError = (...args) => console.error(UI_LOG_PREFIX, ...args);

    window.addEventListener("error", (event) => {
      uiError(
        "window error",
        event.message,
        `${event.filename}:${event.lineno}:${event.colno}`,
        event.error && event.error.stack ? event.error.stack : event.error
      );
    });

    window.addEventListener("unhandledrejection", (event) => {
      uiError("unhandled rejection", event.reason);
    });

    uiLog("script init", { at: new Date().toISOString(), readyState: document.readyState });

    function _fallbackParseChartIds(rawValue) {
      return String(rawValue || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }

    async function _fallbackRunPipeline() {
      const statusEl = document.getElementById("status");
      const runBtn = document.getElementById("runBtn");
      const chartIdsEl = document.getElementById("chartIds");
      const lookbackEl = document.getElementById("lookback");
      const outputDirEl = document.getElementById("outputDir");
      const skipAiEl = document.getElementById("skipAi");

      function setFallbackStatus(message, tone) {
        if (!statusEl) return;
        statusEl.className = "status " + (tone || "");
        statusEl.textContent = message;
      }

      if (runBtn) {
        runBtn.disabled = true;
        runBtn.classList.add("running");
      }
      setFallbackStatus("Working...", "");

      if (!window.fetch) {
        setFallbackStatus("Run failed: browser fetch is unavailable.", "error");
        if (runBtn) {
          runBtn.classList.remove("running");
          runBtn.disabled = false;
        }
        return;
      }

      const payload = {
        chart_ids: _fallbackParseChartIds(chartIdsEl ? chartIdsEl.value : ""),
        lookback_days: Number(lookbackEl ? lookbackEl.value : 7) || 7,
        output_dir: String(outputDirEl ? outputDirEl.value : "").trim(),
        skip_ai: Boolean(skipAiEl && skipAiEl.checked),
      };

      try {
        const resp = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!resp.ok) {
          setFallbackStatus(data.error || "Run failed.", "error");
          return;
        }
        setFallbackStatus("Run complete. Reloading results...", "ok");
        window.location.reload();
      } catch (err) {
        const message = err && err.message ? err.message : String(err || "unknown error");
        setFallbackStatus("Run failed: " + message, "error");
      } finally {
        if (runBtn) {
          runBtn.classList.remove("running");
          runBtn.disabled = false;
        }
      }
    }

    // Assign a resilient fallback first; full init below replaces this with richer behavior.
    window.__runPipeline = _fallbackRunPipeline;

    try {
    const runBtn = document.getElementById("runBtn");
    const statusEl = document.getElementById("status");
    const stageResultsEl = document.getElementById("stageResults");
    const summaryCardsEl = document.getElementById("summaryCards");
    const slackPreviewEl = document.getElementById("slackPreview");
    const slackPayloadEditorEl = document.getElementById("slackPayloadEditor");
    const postSlackPayloadBtn = document.getElementById("postSlackPayloadBtn");
    const copySlackPayloadBtn = document.getElementById("copySlackPayloadBtn");
    const openBlockKitBuilderEl = document.getElementById("openBlockKitBuilder");
    const slackPostStatusEl = document.getElementById("slackPostStatus");
    const chartIdsEl = document.getElementById("chartIds");
    const chartGuideEl = document.getElementById("chartGuide");
    const modeButtons = Array.from(document.querySelectorAll(".mode-btn"));

    uiLog("dom refs", {
      runBtn: !!runBtn,
      statusEl: !!statusEl,
      stageResultsEl: !!stageResultsEl,
      summaryCardsEl: !!summaryCardsEl,
      slackPreviewEl: !!slackPreviewEl,
      slackPayloadEditorEl: !!slackPayloadEditorEl,
      postSlackPayloadBtn: !!postSlackPayloadBtn,
      copySlackPayloadBtn: !!copySlackPayloadBtn,
      openBlockKitBuilderEl: !!openBlockKitBuilderEl,
      slackPostStatusEl: !!slackPostStatusEl,
      chartIdsEl: !!chartIdsEl,
      chartGuideEl: !!chartGuideEl,
      modeButtons: modeButtons.length,
    });

    if (
      !runBtn ||
      !statusEl ||
      !stageResultsEl ||
      !summaryCardsEl ||
      !slackPreviewEl ||
      !slackPayloadEditorEl ||
      !postSlackPayloadBtn ||
      !copySlackPayloadBtn ||
      !openBlockKitBuilderEl ||
      !slackPostStatusEl ||
      !chartIdsEl ||
      !chartGuideEl
    ) {
      throw new Error("Missing one or more required DOM elements for UI initialization.");
    }

    const stageOrder = [
      "01_amplitude_query_charts.json",
      "02_typeform_feedback.json",
      "02b_typeform_feedback_themes.json",
      "02c_app_context_sections.json",
      "02d_ios_release_context.json",
      "03_ai_analysis.json",
      "04_slack_payload_preview.json"
    ];

    const stageTitles = {
      "01_amplitude_query_charts.json": "1) Amplitude Chart Query Results",
      "02_typeform_feedback.json": "2) Typeform Feedback",
      "02b_typeform_feedback_themes.json": "2a) Typeform Feedback Themes",
      "02c_app_context_sections.json": "2b) App Context Sections",
      "02d_ios_release_context.json": "2c) iOS Release Context",
      "03_ai_analysis.json": "3) AI Analysis",
      "04_slack_payload_preview.json": "4) Slack Payload Preview"
    };

    let currentMode = "human";
    let latestStages = {};
    let latestSummary = {};
    let latestSlackPayload = null;
    const chartReferencesById = Object.create(null);

    function setStatus(message, tone = "") {
      statusEl.className = "status " + tone;
      statusEl.textContent = message;
      uiLog("status", { message, tone });
    }

    function setSlackPostStatus(message, tone = "") {
      slackPostStatusEl.className = "status slack-post-status " + tone;
      slackPostStatusEl.textContent = message;
      uiLog("slack-post-status", { message, tone });
    }

    function parseChartIds(input) {
      return input
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }

    function upsertChartReferences(refs) {
      if (!Array.isArray(refs)) return;
      refs.forEach((ref) => {
        if (!ref || typeof ref !== "object") return;
        const chartId = String(ref.chart_id || "").trim();
        if (!chartId) return;
        const chartTypes = Array.isArray(ref.chart_types)
          ? ref.chart_types.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const metricKeys = Array.isArray(ref.metric_keys)
          ? ref.metric_keys.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const contracts = Array.isArray(ref.contracts)
          ? ref.contracts
              .filter((item) => item && typeof item === "object")
              .map((item) => ({
                chart_set: String(item.chart_set || "").trim(),
                group: String(item.group || "").trim(),
                metric_key: String(item.metric_key || "").trim(),
                chart_type: String(item.chart_type || "").trim(),
                status: String(item.status || "").trim(),
                intent: String(item.intent || "").trim(),
                alias_of_metric_key: String(item.alias_of_metric_key || "").trim(),
                chart_reuse_note: String(item.chart_reuse_note || "").trim(),
              }))
          : [];
        chartReferencesById[chartId] = {
          chart_id: chartId,
          chart_title: String(ref.chart_title || `Amplitude chart ${chartId}`),
          chart_link: String(ref.chart_link || `https://app.amplitude.com/analytics/tenant/chart/${chartId}`),
          chart_types: chartTypes,
          metric_keys: metricKeys,
          contracts,
        };
      });
    }

    function getChartReference(chartId) {
      const normalized = String(chartId || "").trim();
      if (!normalized) {
        return {
          chart_id: "-",
          chart_title: "-",
          chart_link: "",
          chart_types: [],
          metric_keys: [],
          contracts: [],
          known: false,
        };
      }
      const knownRef = chartReferencesById[normalized];
      if (knownRef) {
        return { ...knownRef, known: true };
      }
      return {
        chart_id: normalized,
        chart_title: `Unmapped chart ID (${normalized})`,
        chart_link: `https://app.amplitude.com/analytics/tenant/chart/${normalized}`,
        chart_types: [],
        metric_keys: [],
        contracts: [],
        known: false,
      };
    }

    function renderChartGuide() {
      const chartIds = parseChartIds(chartIdsEl.value);
      if (!chartIds.length) {
        chartGuideEl.innerHTML = `
          <p class="chart-guide-head">Chart ID Reference</p>
          <p class="chart-guide-empty">Add one or more chart IDs to preview chart names and links.</p>
        `;
        return;
      }

      const refs = chartIds.map((chartId) => getChartReference(chartId));
      const unknownCount = refs.filter((ref) => !ref.known).length;
      const rows = refs
        .map((ref) => {
          const nameClass = ref.known ? "" : "chart-ref-unknown";
          const chartTypes = Array.isArray(ref.chart_types) && ref.chart_types.length
            ? ref.chart_types.join(", ")
            : "-";
          const contracts = Array.isArray(ref.contracts) ? ref.contracts : [];
          const contractHtml = contracts.length
            ? `<ul class="chart-contract-list">${contracts
                .map((contract) => {
                  const scopeParts = [contract.chart_set, contract.group].filter(Boolean).join("/");
                  const detailParts = [scopeParts, contract.chart_type, contract.status]
                    .filter(Boolean)
                    .join(" | ");
                  const aliasText = contract.alias_of_metric_key
                    ? ` (alias of ${contract.alias_of_metric_key})`
                    : "";
                  const reuseText = contract.chart_reuse_note
                    ? `<br><span class="chart-ref-unknown">${escapeHtml(contract.chart_reuse_note)}</span>`
                    : "";
                  return `<li><strong>${escapeHtml(contract.metric_key || "-")}</strong>${escapeHtml(aliasText)}${detailParts ? `<br>${escapeHtml(detailParts)}` : ""}${reuseText}</li>`;
                })
                .join("")}</ul>`
            : "-";
          const link = ref.chart_link
            ? `<a class="chart-ref-link" href="${escapeHtml(ref.chart_link)}" target="_blank" rel="noreferrer noopener">Open</a>`
            : "-";
          return `
            <tr>
              <td>${escapeHtml(ref.chart_id)}</td>
              <td class="${nameClass}">${escapeHtml(ref.chart_title)}</td>
              <td>${escapeHtml(chartTypes)}</td>
              <td>${contractHtml}</td>
              <td>${link}</td>
            </tr>
          `;
        })
        .join("");

      const unknownNote = unknownCount
        ? `<div class="chart-guide-note">${unknownCount} chart ID(s) are not mapped in the metric dictionary. Double-check before running.</div>`
        : "";

      chartGuideEl.innerHTML = `
        <p class="chart-guide-head">Chart ID Reference</p>
        ${unknownNote}
        <div class="chart-ref-wrap">
          <table class="chart-ref-table">
            <thead>
              <tr>
                <th>Chart ID</th>
                <th>Chart Name</th>
                <th>Chart Type(s)</th>
                <th>Metric Contracts</th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    }

    function pretty(payload) {
      return JSON.stringify(payload, null, 2);
    }

    function loadSlackPayloadEditor(slackPayload) {
      if (!slackPayload || typeof slackPayload !== "object") {
        latestSlackPayload = null;
        slackPayloadEditorEl.value = "";
        setSlackPostStatus("No Slack payload found for this run.", "warn");
        return;
      }

      latestSlackPayload = slackPayload;
      slackPayloadEditorEl.value = pretty(slackPayload);
      setSlackPostStatus(
        "Payload loaded. Review/edit JSON, validate in Block Kit Builder, then post this exact payload.",
        "ok"
      );
    }

    function parseEditedSlackPayload() {
      const raw = String(slackPayloadEditorEl.value || "").trim();
      if (!raw) {
        throw new Error("Slack payload editor is empty.");
      }
      let parsed;
      try {
        parsed = JSON.parse(raw);
      } catch (err) {
        throw new Error("Slack payload JSON is invalid. Fix syntax before posting.");
      }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Slack payload must be a JSON object.");
      }
      return parsed;
    }

    async function copySlackPayload() {
      const raw = String(slackPayloadEditorEl.value || "").trim();
      if (!raw) {
        setSlackPostStatus("Nothing to copy. Run pipeline first.", "warn");
        return;
      }

      try {
        if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(raw);
          setSlackPostStatus("Payload JSON copied to clipboard.", "ok");
          return;
        }
      } catch (_err) {
        // Fall back to manual select/copy flow below.
      }

      slackPayloadEditorEl.focus();
      slackPayloadEditorEl.select();
      setSlackPostStatus("Clipboard API unavailable. Press Cmd/Ctrl+C to copy selected JSON.", "warn");
    }

    async function postEditedSlackPayload() {
      if (!window.fetch) {
        setSlackPostStatus("Cannot post: browser fetch is unavailable.", "error");
        return;
      }

      let payload;
      try {
        payload = parseEditedSlackPayload();
      } catch (err) {
        setSlackPostStatus(err.message || String(err), "error");
        return;
      }

      const confirmPost = window.confirm(
        "Post the currently edited payload to Slack now? This sends exactly the JSON in the editor."
      );
      if (!confirmPost) {
        setSlackPostStatus("Post cancelled.", "warn");
        return;
      }

      postSlackPayloadBtn.disabled = true;
      setSlackPostStatus("Posting edited payload to Slack...", "");
      try {
        const resp = await fetch("/api/post-slack", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payload }),
        });
        const data = await resp.json();
        if (!resp.ok) {
          setSlackPostStatus(data.error || "Slack post failed.", "error");
          return;
        }
        const channel = data.channel || "webhook default";
        const blockCount = data.block_count != null ? String(data.block_count) : "0";
        setSlackPostStatus(
          `Posted to Slack (${channel}, ${blockCount} blocks).`,
          "ok"
        );
      } catch (err) {
        setSlackPostStatus("Slack post failed: " + (err.message || String(err)), "error");
      } finally {
        postSlackPayloadBtn.disabled = false;
      }
    }

    function escapeHtml(value) {
      return String(value).replace(/[<>&\"']/g, (ch) => {
        if (ch === "<") return "&lt;";
        if (ch === ">") return "&gt;";
        if (ch === "&") return "&amp;";
        if (ch === '"') return "&quot;";
        return "&#39;";
      });
    }

    function fmtNumber(value) {
      return typeof value === "number" ? value.toFixed(2) : "-";
    }

    function fmtPct(value) {
      if (typeof value !== "number") return "-";
      const sign = value > 0 ? "+" : "";
      return sign + value.toFixed(2) + "%";
    }

    function fmtPctClass(value) {
      if (typeof value !== "number") return "neutral";
      if (value > 0) return "pos";
      if (value < 0) return "neg";
      return "neutral";
    }

    function formatIso(value) {
      if (!value) return "-";
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) return String(value);
      return dt.toLocaleString();
    }

    function previewText(value, maxChars = 420) {
      const text = String(value || "").trim();
      if (!text) return "";
      if (text.length <= maxChars) return text;
      return text.slice(0, Math.max(1, maxChars - 3)).trimEnd() + "...";
    }

    function fmtMultiline(value) {
      return escapeHtml(String(value || "")).split(String.fromCharCode(10)).join("<br>");
    }

    function renderSummary(summary) {
      latestSummary = summary || {};
      const meta = summary.analysis_meta || {};
      const modelValue = meta.used_model
        ? (meta.fallback_used ? `${meta.used_model} (fallback)` : meta.used_model)
        : "-";
      const items = [
        ["Charts", summary.chart_count != null ? summary.chart_count : 0],
        ["Feedback Items", summary.feedback_count != null ? summary.feedback_count : 0],
        ["Feedback Themes", summary.feedback_theme_count != null ? summary.feedback_theme_count : 0],
        [
          "iOS Release Ingestion",
          summary.ios_release_ingestion_status != null ? summary.ios_release_ingestion_status : "-"
        ],
        ["Context Source", summary.context_source != null ? summary.context_source : "-"],
        ["Model Used", modelValue],
        ["Output Dir", summary.output_dir != null ? summary.output_dir : "-"],
      ];

      summaryCardsEl.innerHTML = items
        .map(([label, value]) => `
          <div class="card">
            <div class="label">${escapeHtml(label)}</div>
            <div class="value">${escapeHtml(String(value))}</div>
          </div>
        `)
        .join("");
    }

    function renderBulletList(items) {
      if (!Array.isArray(items) || !items.length) {
        return '<div class="empty-note">No entries.</div>';
      }
      return `<ul class="human-list">${items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`;
    }

    function humanAmplitudeStage(payload) {
      if (!Array.isArray(payload) || !payload.length) {
        return '<div class="human-block"><div class="empty-note">No chart results.</div></div>';
      }

      const rows = payload.map((item) => {
        const summary = item.summary || {};
        const pct = summary.pct_change_vs_previous;
        const ref = getChartReference(item.chart_id || "");
        const titleClass = ref.known ? "" : "chart-ref-unknown";
        return `
          <tr>
            <td>
              <div>${escapeHtml(item.chart_id || "-")}</div>
              <div class="${titleClass}">${escapeHtml(ref.chart_title || "-")}</div>
            </td>
            <td>${fmtNumber(summary.latest_value)}</td>
            <td>${fmtNumber(summary.previous_value)}</td>
            <td class="value ${fmtPctClass(pct)}">${fmtPct(pct)}</td>
            <td>${escapeHtml((Array.isArray(ref.chart_types) && ref.chart_types.length) ? ref.chart_types.join(", ") : "-")}</td>
            <td>${escapeHtml(summary.metric_kind || summary.response_type || "-")}</td>
          </tr>
        `;
      }).join("");

      const movers = payload
        .map((item) => {
          const summary = item.summary || {};
          const pct = summary.pct_change_vs_previous;
          if (typeof pct !== "number") return null;
          const ref = getChartReference(item.chart_id || "");
          return {
            chartId: item.chart_id || "-",
            chartTitle: ref.chart_title || "-",
            known: ref.known,
            pct,
            mag: Math.abs(pct),
          };
        })
        .filter(Boolean)
        .sort((a, b) => b.mag - a.mag)
        .slice(0, 3);

      const moversHtml = movers.length
        ? `<ul class="human-list">${movers.map((m) => `<li><strong>${escapeHtml(m.chartTitle)}</strong> <span class="${m.known ? "" : "chart-ref-unknown"}">(${escapeHtml(m.chartId)})</span>: <span class="value ${fmtPctClass(m.pct)}">${fmtPct(m.pct)}</span></li>`).join("")}</ul>`
        : '<div class="empty-note">No percentage movers available.</div>';

      return `
        <div class="human-block">
          <div class="human-subtitle">Top Movers</div>
          ${moversHtml}
          <div class="human-subtitle">All Charts</div>
          <div class="human-table-wrap">
            <table class="human-table">
              <thead>
                <tr>
                  <th>Chart ID</th>
                  <th>Latest</th>
                  <th>Previous</th>
                  <th>Delta %</th>
                  <th>Chart Type</th>
                  <th>Response Kind</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function humanFeedbackStage(payload) {
      if (!Array.isArray(payload) || !payload.length) {
        return '<div class="human-block"><div class="empty-note">No feedback responses found.</div></div>';
      }

      const items = payload.map((item) => {
        const submitted = formatIso(item.submitted_at);
        const answers = Array.isArray(item.answers) ? item.answers : [];
        return `
          <li>
            <span class="mono-pill">${escapeHtml(submitted)}</span>
            ${answers.length ? `<div>${answers.map((ans) => `<span class="mono-pill">${escapeHtml(String(ans))}</span>`).join("")}</div>` : '<div class="empty-note">No answers extracted.</div>'}
          </li>
        `;
      }).join("");

      return `
        <div class="human-block">
          <div class="human-subtitle">Recent Feedback (${payload.length})</div>
          <ul class="human-list">${items}</ul>
        </div>
      `;
    }

    function humanFeedbackThemesStage(payload) {
      if (!payload || typeof payload !== "object") {
        return '<div class="human-block"><div class="empty-note">No feedback theme summary available.</div></div>';
      }

      const themes = Array.isArray(payload.themes) ? payload.themes : [];
      const rows = themes.length
        ? themes.map((theme) => {
            const snippets = Array.isArray(theme.representative_snippets) ? theme.representative_snippets : [];
            const snippetPreview = snippets.length ? previewText(snippets.join(" | "), 320) : "-";
            return `
              <tr>
                <td>${escapeHtml(theme.theme_label || theme.theme_key || "-")}</td>
                <td>${escapeHtml(String(theme.mention_count != null ? theme.mention_count : 0))}</td>
                <td>${escapeHtml(snippetPreview)}</td>
              </tr>
            `;
          }).join("")
        : '<tr><td colspan="3">No themes detected.</td></tr>';

      return `
        <div class="human-block">
          <div><span class="mono-pill">feedback items: ${escapeHtml(String(payload.feedback_items_count != null ? payload.feedback_items_count : 0))}</span><span class="mono-pill">snippets: ${escapeHtml(String(payload.feedback_snippets_count != null ? payload.feedback_snippets_count : 0))}</span><span class="mono-pill">themes: ${escapeHtml(String(payload.theme_count != null ? payload.theme_count : 0))}</span></div>
          <div class="human-subtitle">Theme Breakdown</div>
          <div class="human-table-wrap">
            <table class="human-table">
              <thead>
                <tr>
                  <th>Theme</th>
                  <th>Mentions</th>
                  <th>Representative Snippets</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
    }

    function humanContextSectionsStage(payload) {
      if (!payload || typeof payload !== "object") {
        return '<div class="human-block"><div class="empty-note">No app context sections available.</div></div>';
      }

      const baseContext = String(payload.base_app_context || "");
      const activationContext = String(payload.activation_weekly_context || "");
      const source = String(payload.context_source || "unknown");

      return `
        <div class="human-block">
          <div><span class="mono-pill">context source: ${escapeHtml(source)}</span><span class="mono-pill">base chars: ${escapeHtml(String(baseContext.length))}</span><span class="mono-pill">activation chars: ${escapeHtml(String(activationContext.length))}</span></div>
          <div class="human-subtitle">Base App Context (preview)</div>
          <div>${baseContext ? fmtMultiline(previewText(baseContext, 900)) : '<span class="empty-note">No base context text found.</span>'}</div>
          <div class="human-subtitle">Activation Weekly Context (preview)</div>
          <div>${activationContext ? fmtMultiline(previewText(activationContext, 900)) : '<span class="empty-note">No activation context text found.</span>'}</div>
        </div>
      `;
    }

    function humanIosReleaseContextStage(payload) {
      if (!payload || typeof payload !== "object") {
        return '<div class="human-block"><div class="empty-note">No iOS release context available.</div></div>';
      }

      const recent = Array.isArray(payload.recent_releases_with_notes)
        ? payload.recent_releases_with_notes
        : (Array.isArray(payload.recent_releases) ? payload.recent_releases : []);
      const curated = Array.isArray(payload.recent_release_notes) ? payload.recent_release_notes : [];

      const rows = recent.length
        ? recent.map((entry) => {
          const highlights = Array.isArray(entry.highlights) ? entry.highlights : [];
          const highlightsPreview = highlights.slice(0, 2).map((line) => `- ${line}`).join("\\n");
          return `
          <tr>
            <td>${escapeHtml(entry.version || "-")}</td>
            <td>${escapeHtml(entry.build || "-")}</td>
            <td>${escapeHtml(entry.release_date || "-")}</td>
            <td>${escapeHtml(entry.dedupe_key || "-")}</td>
            <td>${entry.notes_available ? '<span class="mono-pill">yes</span>' : '<span class="mono-pill">no</span>'}</td>
            <td>${highlightsPreview ? fmtMultiline(previewText(highlightsPreview, 260)) : '<span class="empty-note">-</span>'}</td>
          </tr>
        `;
        }).join("")
        : '<tr><td colspan="6">No releases in log.</td></tr>';

      const errorLine = payload.ingestion_error
        ? `<div class="empty-note">Ingestion error: ${escapeHtml(String(payload.ingestion_error))}</div>`
        : "";
      const notesErrorLine = payload.release_notes_ingestion_error
        ? `<div class="empty-note">Curated notes error: ${escapeHtml(String(payload.release_notes_ingestion_error))}</div>`
        : "";

      const curatedList = curated.length
        ? `<ul>${curated
            .map((entry) => {
              const version = escapeHtml(entry.version || "-");
              const date = escapeHtml(entry.release_date || "-");
              const highlights = Array.isArray(entry.highlights) ? entry.highlights.slice(0, 2) : [];
              const preview = highlights.length
                ? `<div>${highlights.map((line) => escapeHtml(`- ${line}`)).join("<br/>")}</div>`
                : '<span class="empty-note">No highlights.</span>';
              return `<li><strong>${version}</strong> <span class="empty-note">(${date})</span>${preview}</li>`;
            })
            .join("")}</ul>`
        : '<span class="empty-note">No curated release notes loaded.</span>';

      return `
        <div class="human-block">
          <div>
            <span class="mono-pill">status: ${escapeHtml(String(payload.ingestion_status || "unknown"))}</span>
            <span class="mono-pill">notes status: ${escapeHtml(String(payload.release_notes_ingestion_status || "unknown"))}</span>
            <span class="mono-pill">app id: ${escapeHtml(String(payload.app_id || "-"))}</span>
          </div>
          ${errorLine}
          ${notesErrorLine}
          <div class="human-subtitle">Recent Releases</div>
          <div class="human-table-wrap">
            <table class="human-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Build</th>
                  <th>Release Date (UTC)</th>
                  <th>Dedupe Key</th>
                  <th>Curated Notes</th>
                  <th>Highlights (preview)</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
          <div class="human-subtitle">Curated Release Notes (from file)</div>
          <div>${curatedList}</div>
        </div>
      `;
    }

    function humanAnalysisStage(payload) {
      if (!payload || typeof payload !== "object") {
        return '<div class="human-block"><div class="empty-note">No AI analysis payload.</div></div>';
      }

      const meta = payload.analysis_meta || {};
      const modelMeta = [];
      if (meta.requested_model) modelMeta.push(`requested: ${meta.requested_model}`);
      if (meta.used_model) modelMeta.push(`used: ${meta.used_model}`);
      if (meta.fallback_used) modelMeta.push("fallback: yes");

      return `
        <div class="human-block">
          <div class="human-subtitle">Headline</div>
          <div>${escapeHtml(payload.headline || "-")}</div>
          ${modelMeta.length ? `<div class="human-subtitle">Model</div><div>${modelMeta.map((entry) => `<span class="mono-pill">${escapeHtml(entry)}</span>`).join("")}</div>` : ""}
          <div class="human-subtitle">Key Metrics</div>
          ${renderBulletList(payload.key_changes)}
          <div class="human-subtitle">Insights</div>
          ${renderBulletList(payload.possible_explanations)}
          <div class="human-subtitle">Next Steps</div>
          ${renderBulletList(payload.suggested_actions)}
        </div>
      `;
    }

    function humanSlackStage(payload) {
      if (!payload || typeof payload !== "object") {
        return '<div class="human-block"><div class="empty-note">No Slack payload preview found.</div></div>';
      }
      const blockCount = Array.isArray(payload.blocks) ? payload.blocks.length : 0;
      return `
        <div class="human-block">
          <div class="human-subtitle">Payload Summary</div>
          <div><span class="mono-pill">channel: ${escapeHtml(payload.channel || "webhook default")}</span><span class="mono-pill">blocks: ${escapeHtml(String(blockCount))}</span></div>
          <div class="human-subtitle">Fallback Text</div>
          <div>${escapeHtml(payload.text || "-")}</div>
          <div class="human-subtitle">Review + Post Workflow</div>
          <div class="empty-note">Use the JSON editor panel to review/edit and post this exact payload. Use Block Kit Builder for Slack-accurate rendering.</div>
        </div>
      `;
    }

    function renderHumanStage(filename, payload) {
      if (filename === "01_amplitude_query_charts.json") return humanAmplitudeStage(payload);
      if (filename === "02_typeform_feedback.json") return humanFeedbackStage(payload);
      if (filename === "02b_typeform_feedback_themes.json") return humanFeedbackThemesStage(payload);
      if (filename === "02c_app_context_sections.json") return humanContextSectionsStage(payload);
      if (filename === "02d_ios_release_context.json") return humanIosReleaseContextStage(payload);
      if (filename === "03_ai_analysis.json") return humanAnalysisStage(payload);
      if (filename === "04_slack_payload_preview.json") return humanSlackStage(payload);
      return `<div class="human-block"><div class="empty-note">No renderer for ${escapeHtml(filename)}.</div></div>`;
    }

    function renderMachineStage(payload) {
      return `<pre class="machine-pre">${escapeHtml(pretty(payload))}</pre>`;
    }

    function renderStages(stages) {
      const keys = stageOrder.filter((filename) => Object.prototype.hasOwnProperty.call(stages, filename));
      if (!keys.length) {
        stageResultsEl.innerHTML = "<p>No stage data available.</p>";
        return;
      }

      stageResultsEl.innerHTML = keys
        .map((filename) => {
          const payload = stages[filename];
          const content = currentMode === "human"
            ? renderHumanStage(filename, payload)
            : renderMachineStage(payload);
          const chipLabel = currentMode === "human" ? "Digest" : "JSON";
          const cardClass = currentMode === "human" ? "human-card" : "machine-card";
          return `
            <details class="stage-card ${cardClass}" open>
              <summary>
                <span class="stage-title">${escapeHtml(stageTitles[filename] || filename)}</span>
                <span class="stage-chip">${chipLabel}</span>
              </summary>
              ${content}
            </details>
          `;
        })
        .join("");
    }

    function renderModeMeta(mode) {
      if (mode === "machine") {
        slackPreviewEl.classList.add("hidden");
        return;
      }

      slackPreviewEl.classList.remove("hidden");
    }

    function renderSlackMrkdwn(text) {
      let html = escapeHtml(String(text || ""));
      html = html.replace(/&lt;([^|&]+)\|([^&]+)&gt;/g, (_match, url, label) => {
        return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
      });
      html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
      html = html.replace(/\*(.*?)\*/g, "<strong>$1</strong>");
      html = html.split(String.fromCharCode(10)).join("<br>");
      return html;
    }

    function renderSlackBlock(block) {
      if (!block || typeof block !== "object") {
        return `<div class="slack-block">${escapeHtml(String(block))}</div>`;
      }

      if (block.type === "header") {
        const text = ((block.text || {}).text) || "(header)";
        return `<div class="slack-block slack-header">${escapeHtml(text)}</div>`;
      }

      if (block.type === "divider") {
        return '<div class="slack-divider"></div>';
      }

      if (block.type === "section") {
        const text = ((block.text || {}).text) || "";
        return `<div class="slack-block">${renderSlackMrkdwn(text)}</div>`;
      }

      return `<div class="slack-block"><pre class="machine-pre">${escapeHtml(pretty(block))}</pre></div>`;
    }

    function renderSlackPreview(slackPayload) {
      if (!slackPayload || typeof slackPayload !== "object") {
        slackPreviewEl.innerHTML = "";
        return;
      }

      const channel = slackPayload.channel || "webhook default";
      const blocks = Array.isArray(slackPayload.blocks) ? slackPayload.blocks : [];
      const fallbackText = slackPayload.text || "";

      slackPreviewEl.innerHTML = `
        <div class="slack-preview-head">Slack Preview (local approximation, not Block Kit source of truth)</div>
        <div class="slack-shell">
          <div class="slack-top">
            <span>#${escapeHtml(channel)}</span>
            <span>${escapeHtml(String(blocks.length))} blocks</span>
          </div>
          <div class="slack-body">
            ${fallbackText ? `<div class="slack-fallback">${renderSlackMrkdwn(fallbackText)}</div>` : ""}
            ${blocks.map(renderSlackBlock).join("")}
          </div>
        </div>
      `;
    }

    function setMode(mode) {
      uiLog("setMode called", { mode });
      currentMode = mode;
      modeButtons.forEach((btn) => {
        const isActive = btn.dataset.mode === mode;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
      });
      renderModeMeta(mode);
      renderStages(latestStages);
    }
    window.__setMode = setMode;

    async function loadDefaults() {
      uiLog("loadDefaults:start");
      try {
        const resp = await fetch("/api/defaults");
        uiLog("loadDefaults:response", { ok: resp.ok, status: resp.status });
        if (!resp.ok) return;
        const data = await resp.json();
        uiLog("loadDefaults:data", data);
        if (Array.isArray(data.known_chart_references)) {
          upsertChartReferences(data.known_chart_references);
        }
        if (Array.isArray(data.chart_references)) {
          upsertChartReferences(data.chart_references);
        }
        if (Array.isArray(data.chart_ids) && data.chart_ids.length) {
          chartIdsEl.value = data.chart_ids.join(",");
        }
        if (typeof data.lookback_days === "number") {
          document.getElementById("lookback").value = String(data.lookback_days);
        }
        if (typeof data.default_output_dir === "string") {
          document.getElementById("outputDir").value = data.default_output_dir;
        }
        if (typeof data.skip_ai_analysis === "boolean") {
          document.getElementById("skipAi").checked = data.skip_ai_analysis;
        }
        if (typeof data.block_kit_builder_url === "string" && data.block_kit_builder_url.trim()) {
          openBlockKitBuilderEl.setAttribute("href", data.block_kit_builder_url.trim());
        }
        renderChartGuide();
      } catch (err) {
        uiError("loadDefaults:error", err, err && err.stack ? err.stack : "");
        setStatus("Unable to load defaults.", "warn");
      }
    }

    async function runPipeline() {
      uiLog("runPipeline:start");
      runBtn.disabled = true;
      runBtn.classList.add("running");
      setStatus("Working...", "");

      const payload = {
        chart_ids: parseChartIds(chartIdsEl.value),
        lookback_days: Number(document.getElementById("lookback").value) || 7,
        output_dir: document.getElementById("outputDir").value.trim(),
        skip_ai: document.getElementById("skipAi").checked,
      };
      uiLog("runPipeline:payload", payload);

      try {
        const resp = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        uiLog("runPipeline:response", { ok: resp.ok, status: resp.status });
        const data = await resp.json();
        uiLog("runPipeline:data", data);
        if (!resp.ok) {
          setStatus(data.error || "Run failed.", "error");
          return;
        }

        const summary = data.summary || {};
        const stages = data.stages || {};

        latestStages = stages;
        latestSummary = summary;
        latestSlackPayload = stages["04_slack_payload_preview.json"] || null;
        renderSummary(summary);
        renderSlackPreview(latestSlackPayload);
        loadSlackPayloadEditor(latestSlackPayload);
        renderStages(stages);
        setStatus("Run complete.", "ok");
        uiLog("runPipeline:complete");
      } catch (err) {
        uiError("runPipeline:error", err, err && err.stack ? err.stack : "");
        setStatus("Run failed: " + err.message, "error");
      } finally {
        runBtn.classList.remove("running");
        runBtn.disabled = false;
        uiLog("runPipeline:finally", { runBtnDisabled: runBtn.disabled });
      }
    }

    window.__runPipeline = runPipeline;
    runBtn.onclick = () => {
      uiLog("run button onclick fired");
      return window.__runPipeline();
    };
    copySlackPayloadBtn.addEventListener("click", copySlackPayload);
    postSlackPayloadBtn.addEventListener("click", postEditedSlackPayload);
    openBlockKitBuilderEl.setAttribute("href", "https://app.slack.com/block-kit-builder/");

    modeButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        uiLog("mode button clicked", { mode: btn.dataset.mode || "human" });
        setMode(btn.dataset.mode || "human");
      });
    });
    chartIdsEl.addEventListener("input", renderChartGuide);
    renderChartGuide();
    setStatus("Ready (JS loaded).");
    setSlackPostStatus("Run pipeline to load payload.", "");
    loadDefaults();
    uiLog("initialization complete");
    } catch (err) {
      uiError("fatal init error", err, err && err.stack ? err.stack : "");
    }
    })();
  </script>
</body>
</html>
"""


def _parse_chart_ids(raw_value: Any) -> Optional[List[str]]:
    if isinstance(raw_value, list):
        values = [str(item).strip() for item in raw_value if str(item).strip()]
        return values or None
    if isinstance(raw_value, str):
        values = [item.strip() for item in raw_value.split(",") if item.strip()]
        return values or None
    return None


def _normalize_slack_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Slack payload must be a JSON object.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Slack payload `text` must be a non-empty string.")

    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("Slack payload `blocks` must be an array.")
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValueError(f"Slack payload `blocks[{index}]` must be an object.")

    normalized: Dict[str, Any] = {
        "text": text.strip(),
        "blocks": blocks,
    }

    if payload.get("channel") is not None:
        channel = payload.get("channel")
        if not isinstance(channel, str) or not channel.strip():
            raise ValueError("Slack payload `channel` must be a non-empty string when provided.")
        normalized["channel"] = channel.strip()

    return normalized


def _load_stage_payloads(output_dir: str) -> Dict[str, Any]:
    payloads: Dict[str, Any] = {}
    base = Path(output_dir)
    for filename in STAGE_FILENAMES:
        path = base / filename
        if not path.exists():
            continue
        payloads[filename] = json.loads(path.read_text(encoding="utf-8"))
    return payloads


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _build_defaults_payload(settings: Settings) -> Dict[str, Any]:
    catalog = get_chart_reference_catalog()

    known_chart_references = [catalog[chart_id] for chart_id in sorted(catalog.keys())]
    default_chart_references = [
        catalog.get(chart_id, _fallback_chart_reference(chart_id))
        for chart_id in settings.chart_ids
    ]

    return {
        "chart_ids": settings.chart_ids,
        "chart_references": default_chart_references,
        "known_chart_references": known_chart_references,
        "lookback_days": settings.lookback_days,
        "default_output_dir": "",
        "gemini_model": settings.gemini_model,
        "skip_ai_analysis": settings.skip_ai_analysis,
        "block_kit_builder_url": BLOCK_KIT_BUILDER_URL,
    }


def _fallback_chart_reference(chart_id: str) -> Dict[str, Any]:
    base_ref = get_chart_reference(chart_id)
    return {
        "chart_id": chart_id,
        "chart_title": base_ref["chart_title"],
        "chart_link": base_ref["chart_link"],
        "chart_types": [],
        "metric_keys": [],
        "chart_sets": [],
        "groups": [],
        "statuses": [],
        "contracts": [],
    }


class _Handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send_html(INDEX_HTML)
            return

        if self.path == "/api/defaults":
            try:
                settings = Settings.load()
                self._send_json(HTTPStatus.OK, _build_defaults_payload(settings))
            except Exception as exc:  # pragma: no cover - defensive error path
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        body = self._read_json()

        if self.path == "/api/run":
            try:
                settings = Settings.load()
                chart_ids = _parse_chart_ids(body.get("chart_ids"))
                if chart_ids is not None and chart_ids == settings.chart_ids:
                    # Treat unchanged defaults as "no override" so local runs mirror production.
                    chart_ids = None
                lookback_days = _safe_int(body.get("lookback_days"), settings.lookback_days)
                output_dir_raw = str(body.get("output_dir") or "").strip()
                if output_dir_raw:
                    output_dir = output_dir_raw
                else:
                    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                    output_dir = f"tmp/pipeline-debug-ui/{timestamp}"

                summary = run_local_debug_pipeline(
                    settings=settings,
                    output_dir=output_dir,
                    chart_ids=chart_ids,
                    lookback_days=lookback_days,
                    skip_ai=bool(body.get("skip_ai")),
                )
                stage_payloads = _load_stage_payloads(summary["output_dir"])
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "summary": summary,
                        "stages": stage_payloads,
                    },
                )
            except Exception as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if self.path == "/api/post-slack":
            try:
                settings = Settings.load()
                if not settings.slack_webhook_url:
                    raise ValueError("SLACK_WEBHOOK_URL is required to post from Debug UI.")

                payload = _normalize_slack_payload(body.get("payload"))
                SlackWebhookClient(
                    webhook_url=settings.slack_webhook_url,
                    channel=None,
                ).post_payload(payload)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "channel": payload.get("channel") or "webhook default",
                        "block_count": len(payload.get("blocks") or []),
                    },
                )
            except Exception as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, _format: str, *_args: Any) -> None:
        # Keep terminal output focused on pipeline logs.
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local browser UI for pipeline debugging.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8787, help="Port to listen on.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"Pipeline Debug UI running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopping UI server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
