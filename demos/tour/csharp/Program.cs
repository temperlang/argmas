// A tour of Argmas, from C#: `pack`, a small archiver's command line.
//
// The same program exists for each language Argmas supports, and they all
// print the same text for the same arguments. See demos/README.md for how
// to run them.

using System;
using Argmas;
using TemperLang.Core;
using static Argmas.ArgmasGlobal;

// The command, declared once, with named arguments for Temper's property
// bags. Each handle has its type: `level` gives an int and `files` a list
// of strings.
var cli = new Command(new CommandSpec("pack", about: "Pack files into archives.", version: "1.0.0"));
var verbose = cli.Flag(new FlagSpec("verbose", @short: "v", help: "Say what's happening.", inherited: true));

// A method can't share its class's name in C#, so `command` is Command_.
var add = cli.Command_(new SubcommandSpec("add", about: "Add files to an archive."));
var level = add.OptionOr(Ints, 6, new OptionSpec("level", @short: "l", help: "How hard to compress.", env: "PACK_LEVEL"));
var mode = add.Option(Choices(new[] { "fast", "small" }), new OptionSpec("mode", help: "What to favor."));
var archive = add.Positional(Strings, new PositionalSpec("ARCHIVE", help: "The archive to add to."));
var files = add.Positionals(Strings, new PositionalSpec("FILE", min: 1, help: "Files to add."));

var list = cli.Command_(new SubcommandSpec("list", about: "List an archive's files.", aliases: new[] { "ls" }));
var listed = list.Positional(Strings, new PositionalSpec("ARCHIVE", help: "The archive to list."));

// Values to run with, text to print (help and version), or a mistake.
var result = cli.Parse(args, new OsEnvironment());
switch (result)
{
    case Args parsed:
        if (parsed.Command.Eq(add))
        {
            Console.WriteLine($"add to {parsed.GetValue(archive)}: {string.Join(", ", parsed.GetValue(files))}");
            var source = parsed.Source(level.Param);
            var origin = source.Eq(Source.Absent) ? "default" : source.Name;
            Console.WriteLine($"level: {parsed.GetValue(level)} ({origin})");
            // GetMaybe gives Temper's Optional, for value types as well as
            // references; OrNull makes it a nullable reference.
            Console.WriteLine($"mode: {parsed.GetMaybe(mode).OrNull() ?? "any"}");
        }
        else if (parsed.Command.Eq(list))
        {
            Console.WriteLine($"list {parsed.GetValue(listed)}");
        }
        Console.WriteLine($"verbose: {(parsed.GetValue(verbose) ? "yes" : "no")}");
        break;
    case Output output:
        Console.Write(output.Text());
        break;
    case ArgError error:
        Console.Error.Write(error.Text());
        break;
}
return result.ExitStatus;

// The process's environment variables, which Argmas reads through this
// interface, so parsing touches nothing outside on its own.
class OsEnvironment : IEnvironment
{
    public string? Get(string name) => System.Environment.GetEnvironmentVariable(name);
}
