// The site's section examples, from Java.
//
// Each `snippet:` block is shown on the site under its section, beside the
// same example in every other language; demos/run.py runs this program in
// each language and checks it prints demos/tour/examples.txt.

import static argmas.ArgmasGlobal.choices;
import static argmas.ArgmasGlobal.directories;
import static argmas.ArgmasGlobal.ints;
import static argmas.ArgmasGlobal.paths;
import static argmas.ArgmasGlobal.strings;

import argmas.ArgError;
import argmas.Command;
import argmas.CommandSpec;
import argmas.FlagSpec;
import argmas.OptionSpec;
import argmas.Output;
import argmas.ParseResult;
import argmas.PositionalSpec;
import argmas.Style;
import argmas.SubcommandSpec;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

public class Examples {
    // snippet: styles
    static Command frob(Style style) {
        var cli = new Command(new CommandSpec.Builder().name("frob").about("Frobnicate files.").style(style).build());
        cli.flag(new FlagSpec.Builder().name("verbose").short_("v").help("Say more.").build());
        cli.optionOr(ints, 3, new OptionSpec.Builder().name("level").short_("l").help("How hard.").build());
        cli.positionals(strings, new PositionalSpec.Builder().name("FILE").help("Files to frobnicate.").build());
        return cli;
    }
    // end snippet

    // snippet: messages
    static Command frobWith(Map<String, String> messages) {
        var cli = new Command(new CommandSpec.Builder().name("frob").about("Frobnicate files.").build());
        cli.optionOr(ints, 3, new OptionSpec.Builder().name("level").short_("l").help("How hard.").build());
        cli.setMessages(messages);
        return cli;
    }
    // end snippet

    public static void main(String[] argv) {
        // snippet: styles
        var gnu = frob(Style.gnu);
        var go = frob(Style.singleDash);
        var windows = frob(Style.windows);
        // end snippet

        // snippet: subcommands
        var git = new Command(new CommandSpec.Builder().name("minigit").about("Track files.").build());
        var quiet = git.flag(new FlagSpec.Builder().name("quiet").short_("q").help("Say less.").inherited(true).build());
        var repo = git.option(directories, new OptionSpec.Builder().name("dir").help("Where the repository is.").build());

        var add = git.subcommand(new SubcommandSpec.Builder().name("add").about("Add files.").build());
        var force = add.flag(new FlagSpec.Builder().name("force").short_("f").help("Add ignored files too.").build());
        var added = add.positionals(paths, new PositionalSpec.Builder().name("PATH").min(1).help("Files to add.").build());

        var rm = git.subcommand(new SubcommandSpec.Builder().name("rm").about("Remove files.").aliases(List.of("remove")).build());
        // end snippet

        // snippet: completions
        var cli = new Command(new CommandSpec.Builder().name("frob").completions(true).build());
        cli.flag(new FlagSpec.Builder().name("verbose").short_("v").help("Say more.").build());
        cli.option(choices(List.of("fast", "slow")), new OptionSpec.Builder().name("mode").help("How to go about it.").build());
        cli.option(paths, new OptionSpec.Builder().name("out").help("Where to write.").build());
        // end snippet

        // snippet: messages
        var english = frobWith(Map.of());
        // A partial translation: what isn't set stays English.
        var german = frobWith(Map.of(
            "usage", "Aufruf: {command}",
            "usage.options", "[OPTIONEN]",
            "help.options", "Optionen:",
            "help.default", "[Vorgabe: {value}]",
            "error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?",
            "error.tryHelp", "Mehr dazu mit '{command} {help}'."));
        // A typo in a key is a mistake in the spec, found on the first run.
        var typo = frobWith(Map.of("usge", "Aufruf: {command}"));
        // end snippet

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
    }

    // Parses a command line's words after the program's name, split at
    // spaces, and prints the line, any text Argmas gives, and the exit
    // status.
    static void show(Command command, String line) {
        var words = Arrays.asList(line.split(" "));
        ParseResult result = command.parse(words.subList(1, words.size()));
        var out = new StringBuilder("$ ").append(line).append("\n");
        if (result instanceof Output output) {
            out.append(output.text());
        } else if (result instanceof ArgError error) {
            out.append(error.text());
        }
        out.append("(exit status ").append(result.getExitStatus()).append(")\n\n");
        System.out.print(out);
    }
}
