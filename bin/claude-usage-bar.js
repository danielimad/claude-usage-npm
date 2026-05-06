#!/usr/bin/env node
"use strict";

const { install, uninstall, start, stop, status } = require("../lib/commands");

const cmd = process.argv[2];
const USAGE = `
  claude-usage <command>

  Commands:
    install     Install and start the menu bar app (runs on every login)
    uninstall   Remove the menu bar app and LaunchAgent
    start       Start the menu bar app now
    stop        Stop the menu bar app (does not uninstall)
    status      Show whether the app is running
`;

(async () => {
  switch (cmd) {
    case "install":   await install();   break;
    case "uninstall": await uninstall(); break;
    case "start":     await start();     break;
    case "stop":      await stop();      break;
    case "status":    await status();    break;
    default:
      console.log(USAGE);
      process.exit(cmd ? 1 : 0);
  }
})();
