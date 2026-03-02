I think we overcomplicated this. I want to try rebuilding this from scratch with the minimal set of requirements and code.

My personal goal is:

Build 3-5 demo agents and host them publicly, so I can get hired as an AI automation freelancer. Nobody hires an AI freelancer with zero proof of work.

I want to build 3-5 demos these and put them on GitHub with live demos:

This portfolio should take a weekend to build. The first demo is Vector, a data analysis agent for product teams.

Let's get started. 
Overall, this is an exercise is building an agent for a business.
We want to use Google ADK (Python), we will use gemini 3 flash.
Before we proceed to build, I want to prototype the UX using ascii diagrams.
I want to ensure we build using Agent Native Architecture.
I am building this proof of concept for eeva, but I want to make this available to others. It is an open source project. I have an existing workflow that doesn't have Agent Native Architecture. 
Let's come up with a 1 pager PRD. Ask me one question at a time.
The overall objective of the agent is to help a product team move faster.
The agent automates data analysis and reporting by pulling metrics (Amplitude), release notes (App Store), and customer feedback (Typeform) through integrations, then synthesizes them with deep knowledge of product flows (using a context document containing key flows, product surfaces) to generate actionable reports for product teams. It will post reports in Slack. We need the ability for the user to preview and adjust reports before they are posted to Slack. The preview should match what would be generated with BlockKit docs/API from Slack.