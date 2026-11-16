// A tour of Argmas, from Java: `pack`, a small archiver's command line.
//
// The same program exists for each language Argmas supports, and they all
// print the same text for the same arguments. See demos/README.md for how
// to run them.

import static argmas.ArgmasGlobal.choices;
import static argmas.ArgmasGlobal.ints;
import static argmas.ArgmasGlobal.strings;

import argmas.ArgError;
import argmas.Args;
import argmas.Command;
import argmas.CommandSpec;
import argmas.FlagSpec;
import argmas.OptionSpec;
import argmas.Output;
import argmas.ParseResult;
import argmas.PositionalSpec;
import argmas.Source;
import argmas.SubcommandSpec;
import java.util.List;

public class Tour {
    public static void main(String[] argv) {
        // The command, declared once, with a builder for each of Temper's
        // property bags. Each handle has its type: `level` gives an Integer
        // and `files` a List<String>.
        var cli = new Command(new CommandSpec.Builder().name("pack").about("Pack files into archives.").version("1.0.0").build());
        // `short` is a keyword in Java, so its setter is `short_`.
        var verbose = cli.flag(new FlagSpec.Builder().name("verbose").short_("v").help("Say what's happening.").inherited(true).build());

        var add = cli.command(new SubcommandSpec.Builder().name("add").about("Add files to an archive.").build());
        var level = add.optionOr(ints, 6, new OptionSpec.Builder().name("level").short_("l").help("How hard to compress.").env("PACK_LEVEL").build());
        var mode = add.option(choices(List.of("fast", "small")), new OptionSpec.Builder().name("mode").help("What to favor.").build());
        var archive = add.positional(strings, new PositionalSpec.Builder().name("ARCHIVE").help("The archive to add to.").build());
        var files = add.positionals(strings, new PositionalSpec.Builder().name("FILE").min(1).help("Files to add.").build());

        var list = cli.command(new SubcommandSpec.Builder().name("list").about("List an archive's files.").aliases(List.of("ls")).build());
        var listed = list.positional(strings, new PositionalSpec.Builder().name("ARCHIVE").help("The archive to list.").build());

        // Values to run with, text to print (help and version), or a mistake.
        // Argmas reads environment variables through its one-method
        // Environment interface, here a lambda, so parsing touches nothing
        // outside on its own.
        ParseResult result = cli.parse(List.of(argv), System::getenv);
        if (result instanceof Args args) {
            if (args.getCommand().eq(add)) {
                System.out.println("add to " + args.getValue(archive) + ": " + String.join(", ", args.getValue(files)));
                var source = args.source(level.param);
                var origin = source.eq(Source.absent) ? "default" : source.getName();
                System.out.println("level: " + args.getValue(level) + " (" + origin + ")");
                var chosen = args.getMaybe(mode);
                System.out.println("mode: " + (chosen != null ? chosen : "any"));
            } else if (args.getCommand().eq(list)) {
                System.out.println("list " + args.getValue(listed));
            }
            System.out.println("verbose: " + (args.getValue(verbose) ? "yes" : "no"));
        } else if (result instanceof Output output) {
            System.out.print(output.text());
        } else if (result instanceof ArgError error) {
            System.err.print(error.text());
        }
        System.exit(result.getExitStatus());
    }
}
