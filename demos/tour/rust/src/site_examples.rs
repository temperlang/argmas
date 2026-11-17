//! The site's section examples, from Rust.
//!
//! Each `snippet:` block is shown on the site under its section, beside the
//! same example in every other language; demos/run.py runs this program in
//! each language and checks it prints demos/tour/examples.txt.

// The snippets declare handles that this program doesn't read.
#![allow(unused_variables)]

use std::sync::Arc;

use argmas::builders::{
    CommandSpecBuilder, FlagSpecBuilder, OptionSpecBuilder, PositionalSpecBuilder, SubcommandSpecBuilder,
};
use argmas::{choices, directories, ints, paths, strings, ArgError, Command, Output, ParseResultTrait, Style};

/// Temper's strings are `Arc<String>` in Rust.
fn s(text: &str) -> Arc<String> {
    Arc::new(text.to_string())
}

// snippet: styles
fn frob(style: Style) -> Command {
    let cli = Command::new(
        CommandSpecBuilder { name: s("frob") }.options().about(s("Frobnicate files.")).style(style).build(),
    );
    cli.flag(FlagSpecBuilder { name: s("verbose") }.options().short(s("v")).help(s("Say more.")).build());
    cli.option_or(
        ints(),
        3,
        OptionSpecBuilder { name: s("level") }.options().short(s("l")).help(s("How hard.")).build(),
    );
    cli.positionals(
        strings(),
        PositionalSpecBuilder { name: s("FILE") }.options().help(s("Files to frobnicate.")).build(),
    );
    cli
}
// end snippet

// snippet: messages
fn frob_with(messages: &[(&str, &str)]) -> Command {
    let cli = Command::new(CommandSpecBuilder { name: s("frob") }.options().about(s("Frobnicate files.")).build());
    cli.option_or(
        ints(),
        3,
        OptionSpecBuilder { name: s("level") }.options().short(s("l")).help(s("How hard.")).build(),
    );
    // set_messages takes Temper's map type, so a loop is simpler.
    for (key, template) in messages {
        cli.set_message(*key, *template);
    }
    cli
}
// end snippet

/// Parses a command line's words after the program's name, split at
/// spaces, and prints the line, any text Argmas gives, and the exit status.
fn show(command: &Command, line: &str) {
    let words: Vec<Arc<String>> = line.split(' ').skip(1).map(s).collect();
    let result = command.parse(words, None);
    println!("$ {line}");
    if let Some(output) = temper_core::cast::<Output>(result.clone()) {
        print!("{}", output.text(None));
    } else if let Some(error) = temper_core::cast::<ArgError>(result.clone()) {
        print!("{}", error.text(None));
    }
    println!("(exit status {})\n", result.exit_status());
}

fn main() {
    // snippet: styles
    let gnu = frob(Style::gnu());
    let go = frob(Style::single_dash());
    let windows = frob(Style::windows());
    // end snippet

    // snippet: subcommands
    let git = Command::new(CommandSpecBuilder { name: s("minigit") }.options().about(s("Track files.")).build());
    let quiet = git.flag(
        FlagSpecBuilder { name: s("quiet") }.options().short(s("q")).help(s("Say less.")).inherited(true).build(),
    );
    let repo = git.option(
        directories(),
        OptionSpecBuilder { name: s("dir") }.options().help(s("Where the repository is.")).build(),
    );

    let add = git.subcommand(SubcommandSpecBuilder { name: s("add") }.options().about(s("Add files.")).build());
    let force = add.flag(
        FlagSpecBuilder { name: s("force") }.options().short(s("f")).help(s("Add ignored files too.")).build(),
    );
    let added = add.positionals(
        paths(),
        PositionalSpecBuilder { name: s("PATH") }.options().min(1).help(s("Files to add.")).build(),
    );

    let rm = git.subcommand(
        SubcommandSpecBuilder { name: s("rm") }
            .options()
            .about(s("Remove files."))
            .aliases(Arc::new(vec![s("remove")]))
            .build(),
    );
    // end snippet

    // snippet: completions
    let cli = Command::new(CommandSpecBuilder { name: s("frob") }.options().completions(true).build());
    cli.flag(FlagSpecBuilder { name: s("verbose") }.options().short(s("v")).help(s("Say more.")).build());
    cli.option(
        choices([s("fast"), s("slow")]),
        OptionSpecBuilder { name: s("mode") }.options().help(s("How to go about it.")).build(),
    );
    cli.option(paths(), OptionSpecBuilder { name: s("out") }.options().help(s("Where to write.")).build());
    // end snippet

    // snippet: messages
    let english = frob_with(&[]);
    // A partial translation: what isn't set stays English.
    let german = frob_with(&[
        ("usage", "Aufruf: {command}"),
        ("usage.options", "[OPTIONEN]"),
        ("help.options", "Optionen:"),
        ("help.default", "[Vorgabe: {value}]"),
        ("error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?"),
        ("error.tryHelp", "Mehr dazu mit '{command} {help}'."),
    ]);
    // A typo in a key is a mistake in the spec, found on the first run.
    let typo = frob_with(&[("usge", "Aufruf: {command}")]);
    // end snippet

    show(&gnu, "frob --help");
    show(&gnu, "frob --level=high a.txt");
    show(&go, "frob -help");
    show(&go, "frob -level=high a.txt");
    show(&windows, "frob /?");
    show(&windows, "frob /level:high a.txt");
    show(&git, "minigit -q add a.txt");
    show(&git, "minigit help add");
    show(&git, "minigit ad a.txt");
    show(&git, "minigit add --dir repo a.txt");
    show(&cli, "frob --help");
    show(&cli, "frob __complete 0 --mo");
    show(&cli, "frob __complete 1 --mode f");
    show(&english, "frob --levle 5");
    show(&german, "frob --help");
    show(&german, "frob --levle 5");
    show(&typo, "frob --help");
}
