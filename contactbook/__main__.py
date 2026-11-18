import argparse
from pathlib import Path

import uvicorn

from .api import create_app, new_sessions
from .demo import run


def main():
    parser = argparse.ArgumentParser(description="A local owner-scoped research contact book")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Run the self-contained two-workspace example")
    serve = commands.add_parser("serve", help="Open a persistent contact book on loopback")
    serve.add_argument("--database", type=Path, default=Path("contacts.sqlite3"))
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "demo":
        run()
        return
    sessions = new_sessions()
    app = create_app(args.database, sessions)
    print("Temporary bearer tokens for this local session", flush=True)
    for workspace, token in sessions.items():
        print(f"{workspace}  {token}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
