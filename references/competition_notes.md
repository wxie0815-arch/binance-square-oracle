# Competition Alignment Notes

This file records the external constraints used to shape the repository for a Binance Agent competition submission.

## Official Sources Checked

- OpenClaw skills documentation
- OpenClaw dependency-install documentation
- Binance Skills Hub official GitHub repository
- Binance Academy article about building a Binance Square AI agent skill

## Secondary Contest Reporting Reviewed

Some contest-specific details were easier to find through secondary reports than through a single canonical announcement page.
Those reports described a Binance / OpenClaw agent competition with Binance-themed agent submissions, public repository delivery, and prize incentives.

Because the official contest page was not available in a single stable source during review, implementation decisions were based primarily on official platform documentation plus official Binance Skills Hub materials.

## Design Decisions Taken

1. The repository now treats `SKILL.md` as the primary product.
2. The main execution path is OpenClaw-native instead of a hardcoded hidden model endpoint.
3. Official Binance skills are the preferred integration layer for data and publishing.
4. The Python code is retained as a prototype path, not the core contest integration path.
5. Missing-submodule risk was removed by vendoring local writing rules into the repository.

## Why This Helps A Submission

- clearer official ecosystem alignment
- easier install story in OpenClaw
- better reliability for judges and reviewers
- preserved product differentiation through style routing and publish-ready output
