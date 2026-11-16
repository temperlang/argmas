// A tour of Argmas, from JavaScript: `pack`, a small archiver's command
// line.
//
// The same program exists for each language Argmas supports, and they all
// print the same text for the same arguments. See demos/README.md for how
// to run them.

import process from "node:process";
import {
  ArgError, Args, Command, CommandSpec, FlagSpec, OptionSpec, Output, PositionalSpec, Source, SubcommandSpec, choices,
  ints, strings,
} from "argmas";

// The command, declared once. Each argument's handle has its type: `level`
// gives a number and `files` an array of strings.
const cli = new Command(CommandSpec.new({ name: "pack", about: "Pack files into archives.", version: "1.0.0" }));
const verbose = cli.flag(FlagSpec.new({ name: "verbose", short: "v", help: "Say what's happening.", inherited: true }));

const add = cli.subcommand(SubcommandSpec.new({ name: "add", about: "Add files to an archive." }));
const level = add.optionOr(ints, 6, OptionSpec.new({ name: "level", short: "l", help: "How hard to compress.", env: "PACK_LEVEL" }));
const mode = add.option(choices(["fast", "small"]), OptionSpec.new({ name: "mode", help: "What to favor." }));
const archive = add.positional(strings, PositionalSpec.new({ name: "ARCHIVE", help: "The archive to add to." }));
const files = add.positionals(strings, PositionalSpec.new({ name: "FILE", min: 1, help: "Files to add." }));

const list = cli.subcommand(SubcommandSpec.new({ name: "list", about: "List an archive's files.", aliases: ["ls"] }));
const listed = list.positional(strings, PositionalSpec.new({ name: "ARCHIVE", help: "The archive to list." }));

// Argmas reads environment variables through an object with `get`, so
// parsing touches nothing outside on its own.
const env = { get: (name) => process.env[name] ?? null };

// Values to run with, text to print (help and version), or a mistake.
const result = cli.parse(process.argv.slice(2), env);
if (result instanceof Args) {
  const args = result;
  if (args.command.eq(add)) {
    console.log(`add to ${args.getValue(archive)}: ${args.getValue(files).join(", ")}`);
    const source = args.source(level.param);
    const origin = source.eq(Source.absent) ? "default" : source.name;
    console.log(`level: ${args.getValue(level)} (${origin})`);
    console.log(`mode: ${args.getMaybe(mode) ?? "any"}`);
  } else if (args.command.eq(list)) {
    console.log(`list ${args.getValue(listed)}`);
  }
  console.log(`verbose: ${args.getValue(verbose) ? "yes" : "no"}`);
} else if (result instanceof Output) {
  process.stdout.write(result.text());
} else if (result instanceof ArgError) {
  process.stderr.write(result.text());
}
process.exitCode = result.exitStatus;
