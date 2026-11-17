// The site's section examples, from JavaScript.
//
// Each `snippet:` block is shown on the site under its section, beside the
// same example in every other language; demos/run.py runs this program in
// each language and checks it prints demos/tour/examples.txt.

import process from "node:process";
import {
  ArgError, Command, CommandSpec, FlagSpec, OptionSpec, Output, PositionalSpec, Style, SubcommandSpec, choices,
  directories, ints, paths, strings,
} from "argmas";

// snippet: styles
function frob(style) {
  const cli = new Command(CommandSpec.new({ name: "frob", about: "Frobnicate files.", style }));
  cli.flag(FlagSpec.new({ name: "verbose", short: "v", help: "Say more." }));
  cli.optionOr(ints, 3, OptionSpec.new({ name: "level", short: "l", help: "How hard." }));
  cli.positionals(strings, PositionalSpec.new({ name: "FILE", help: "Files to frobnicate." }));
  return cli;
}

const gnu = frob(Style.gnu);
const go = frob(Style.singleDash);
const windows = frob(Style.windows);
// end snippet

// snippet: subcommands
const git = new Command(CommandSpec.new({ name: "minigit", about: "Track files." }));
const quiet = git.flag(FlagSpec.new({ name: "quiet", short: "q", help: "Say less.", inherited: true }));
const repo = git.option(directories, OptionSpec.new({ name: "dir", help: "Where the repository is." }));

const add = git.subcommand(SubcommandSpec.new({ name: "add", about: "Add files." }));
const force = add.flag(FlagSpec.new({ name: "force", short: "f", help: "Add ignored files too." }));
const added = add.positionals(paths, PositionalSpec.new({ name: "PATH", min: 1, help: "Files to add." }));

const rm = git.subcommand(SubcommandSpec.new({ name: "rm", about: "Remove files.", aliases: ["remove"] }));
// end snippet

// snippet: completions
const cli = new Command(CommandSpec.new({ name: "frob", completions: true }));
cli.flag(FlagSpec.new({ name: "verbose", short: "v", help: "Say more." }));
cli.option(choices(["fast", "slow"]), OptionSpec.new({ name: "mode", help: "How to go about it." }));
cli.option(paths, OptionSpec.new({ name: "out", help: "Where to write." }));
// end snippet

// snippet: messages
function frobWith(messages) {
  const cli = new Command(CommandSpec.new({ name: "frob", about: "Frobnicate files." }));
  cli.optionOr(ints, 3, OptionSpec.new({ name: "level", short: "l", help: "How hard." }));
  cli.setMessages(messages);
  return cli;
}

const english = frobWith(new Map());
// A partial translation: what isn't set stays English.
const german = frobWith(new Map([
  ["usage", "Aufruf: {command}"],
  ["usage.options", "[OPTIONEN]"],
  ["help.options", "Optionen:"],
  ["help.default", "[Vorgabe: {value}]"],
  ["error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?"],
  ["error.tryHelp", "Mehr dazu mit '{command} {help}'."],
]));
// A typo in a key is a mistake in the spec, found on the first run.
const typo = frobWith(new Map([["usge", "Aufruf: {command}"]]));
// end snippet

// Parses a command line's words after the program's name, split at spaces,
// and prints the line, any text Argmas gives, and the exit status.
function show(command, line) {
  const result = command.parse(line.split(" ").slice(1));
  let out = `$ ${line}\n`;
  if (result instanceof Output || result instanceof ArgError) out += result.text();
  process.stdout.write(`${out}(exit status ${result.exitStatus})\n\n`);
}

show(gnu, "frob --help");
show(gnu, "frob --level=high a.txt");
show(go, "frob -help");
show(go, "frob -level=high a.txt");
show(windows, "frob /?");
show(windows, "frob /level:high a.txt");
show(git, "minigit -q add a.txt");
show(git, "minigit help add");
show(git, "minigit ad a.txt");
show(git, "minigit add --dir repo a.txt");
show(cli, "frob --help");
show(cli, "frob __complete 0 --mo");
show(cli, "frob __complete 1 --mode f");
show(english, "frob --levle 5");
show(german, "frob --help");
show(german, "frob --levle 5");
show(typo, "frob --help");
