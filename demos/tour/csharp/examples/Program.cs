// The site's section examples, from C#.
//
// Each `snippet:` block is shown on the site under its section, beside the
// same example in every other language; demos/run.py runs this program in
// each language and checks it prints demos/tour/examples.txt.

using System;
using System.Collections.Generic;
using System.Linq;
using Argmas;
using static Argmas.ArgmasGlobal;

// snippet: styles
Command Frob(Style style)
{
    var cli = new Command(new CommandSpec("frob", about: "Frobnicate files.", style: style));
    cli.Flag(new FlagSpec("verbose", @short: "v", help: "Say more."));
    cli.OptionOr(Ints, 3, new OptionSpec("level", @short: "l", help: "How hard."));
    cli.Positionals(Strings, new PositionalSpec("FILE", help: "Files to frobnicate."));
    return cli;
}

var gnu = Frob(Style.Gnu);
var go = Frob(Style.SingleDash);
var windows = Frob(Style.Windows);
// end snippet

// snippet: subcommands
var git = new Command(new CommandSpec("minigit", about: "Track files."));
var quiet = git.Flag(new FlagSpec("quiet", @short: "q", help: "Say less.", inherited: true));
var repo = git.Option(Directories, new OptionSpec("dir", help: "Where the repository is."));

var add = git.Subcommand(new SubcommandSpec("add", about: "Add files."));
var force = add.Flag(new FlagSpec("force", @short: "f", help: "Add ignored files too."));
var added = add.Positionals(Paths, new PositionalSpec("PATH", min: 1, help: "Files to add."));

var rm = git.Subcommand(new SubcommandSpec("rm", about: "Remove files.", aliases: new[] { "remove" }));
// end snippet

// snippet: completions
var cli = new Command(new CommandSpec("frob", completions: true));
cli.Flag(new FlagSpec("verbose", @short: "v", help: "Say more."));
cli.Option(Choices(new[] { "fast", "slow" }), new OptionSpec("mode", help: "How to go about it."));
cli.Option(Paths, new OptionSpec("out", help: "Where to write."));
// end snippet

// snippet: messages
Command FrobWith(Dictionary<string, string> messages)
{
    var cli = new Command(new CommandSpec("frob", about: "Frobnicate files."));
    cli.OptionOr(Ints, 3, new OptionSpec("level", @short: "l", help: "How hard."));
    cli.SetMessages(messages);
    return cli;
}

var english = FrobWith(new());
// A partial translation: what isn't set stays English.
var german = FrobWith(new()
{
    ["usage"] = "Aufruf: {command}",
    ["usage.options"] = "[OPTIONEN]",
    ["help.options"] = "Optionen:",
    ["help.default"] = "[Vorgabe: {value}]",
    ["error.unknownOption.suggest"] = "unbekannte Option {option}; meinten Sie {suggestion}?",
    ["error.tryHelp"] = "Mehr dazu mit '{command} {help}'.",
});
// A typo in a key is a mistake in the spec, found on the first run.
var typo = FrobWith(new() { ["usge"] = "Aufruf: {command}" });
// end snippet

Show(gnu, "frob --help");
Show(gnu, "frob --level=high a.txt");
Show(go, "frob -help");
Show(go, "frob -level=high a.txt");
Show(windows, "frob /?");
Show(windows, "frob /level:high a.txt");
Show(git, "minigit -q add a.txt");
Show(git, "minigit help add");
Show(git, "minigit ad a.txt");
Show(git, "minigit add --dir repo a.txt");
Show(cli, "frob --help");
Show(cli, "frob __complete 0 --mo");
Show(cli, "frob __complete 1 --mode f");
Show(english, "frob --levle 5");
Show(german, "frob --help");
Show(german, "frob --levle 5");
Show(typo, "frob --help");

// Parses a command line's words after the program's name, split at spaces,
// and prints the line, any text Argmas gives, and the exit status.
static void Show(Command command, string line)
{
    var result = command.Parse(line.Split(' ').Skip(1).ToList());
    var text = result switch
    {
        Output output => output.Text(),
        ArgError error => error.Text(),
        _ => "",
    };
    Console.Write($"$ {line}\n{text}(exit status {result.ExitStatus})\n\n");
}
