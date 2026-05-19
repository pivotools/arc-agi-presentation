You are an expert in python programming and creating presentations for technical audience.

# Development workflow
In this project, we are creating a presentation for a conference using reveal.js(http://revealjs.com/) and quarto (quarto.org). We create mermaid diagrams to illustrate our content sometimes (mermaid.ai).
## Virtualenv setup
Always activate the venv in `.venv` in the project root:
```bash
source /workspaces/pivotools-quarto-blog/bin/activate
```
## Which file is where
- The presentation markdown: `posts/agentic_coding_arc_agi/presentation.qmd`
- The rendered HTML presentation: `posts/agentic_coding_arc_agi/presentation-html/presentation.html`
## How to render the presentation
```bash
quarto render posts/agentic_coding_arc_agi/presentation.qmd --execute --to revealjs
```
## Tips
In order to check if the presentation renders correctly and fulfils the requirements of the user, you can render a screenshot of the relevant page of the preentation using google chrome headless.