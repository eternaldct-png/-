# Paper search setup

Literature search and paper acquisition use [Paper Search CLI](https://github.com/fcakyon/paper-search-cli). Other skills do not require it. It needs uv and Python 3.10+, with no Docker or MCP server.

Check `paper-search --help`. If missing, install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
uv tool install 'git+https://github.com/fcakyon/paper-search-cli'
paper-search sources
paper-search search 'object detection' -s crossref -n 3
```

If the executable is not on PATH, run `uv tool update-shell` and open a new shell. Update an existing installation with `uv tool upgrade paper-search-cli`.

Inspect the search JSON's `errors` field before reporting success. Configure optional provider credentials using the CLI's [.env.example](https://github.com/fcakyon/paper-search-cli/blob/main/.env.example) in `~/.config/paper-search-mcp/.env`. These legacy names remain supported. IEEE, Scopus, and Web of Science need credentials, so select Scopus and Web of Science explicitly. Never print keys or promise paywalled PDF access from a metadata key.
