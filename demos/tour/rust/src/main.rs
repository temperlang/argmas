//! A tour of Argmas, from Rust: `pack`, a small archiver's command line.
//!
//! The same program exists for each language Argmas supports, and they all
//! print the same text for the same arguments. See demos/README.md for how
//! to run them.

use std::process::ExitCode;
use std::sync::Arc;

use argmas::builders::{
    CommandSpecBuilder, FlagSpecBuilder, OptionSpecBuilder, PositionalSpecBuilder, SubcommandSpecBuilder,
};
use argmas::{
    choices, ints, strings, ArgError, Args, Command, Environment, EnvironmentTrait, Output,
    ParseResultTrait, Source,
};

/// Temper's strings are `Arc<String>` in Rust.
fn s(text: &str) -> Arc<String> {
    Arc::new(text.to_string())
}

/// The process's environment variables, which Argmas reads through its
/// `Environment` interface, so parsing touches nothing outside on its own.
/// Types that implement a Temper interface wrap an `Arc`, and say which
/// interfaces they implement with `impl_any_value_trait!`.
#[derive(Clone)]
struct OsEnvironment(Arc<()>);

impl EnvironmentTrait for OsEnvironment {
    fn clone_boxed(&self) -> Environment {
        Environment::new(self.clone())
    }

    fn get(&self, name: Arc<String>) -> Option<Arc<String>> {
        std::env::var(name.as_str()).ok().map(Arc::new)
    }
}

temper_core::impl_any_value_trait!(OsEnvironment, [Environment]);

fn main() -> ExitCode {
    // The command, declared once, with builders for Temper's property
    // bags. Each handle has its type: `level` gives an i32 and `files` a
    // list of strings.
    let cli = Command::new(
        CommandSpecBuilder { name: s("pack") }.options().about(s("Pack files into archives.")).version(s("1.0.0")).build(),
    );
    let verbose = cli.flag(
        FlagSpecBuilder { name: s("verbose") }
            .options()
            .short(s("v"))
            .help(s("Say what's happening."))
            .inherited(true)
            .build(),
    );

    let add = cli.subcommand(SubcommandSpecBuilder { name: s("add") }.options().about(s("Add files to an archive.")).build());
    let level = add.option_or(
        ints(),
        6,
        OptionSpecBuilder { name: s("level") }
            .options()
            .short(s("l"))
            .help(s("How hard to compress."))
            .env(s("PACK_LEVEL"))
            .build(),
    );
    let mode = add.option(
        choices([s("fast"), s("small")]),
        OptionSpecBuilder { name: s("mode") }.options().help(s("What to favor.")).build(),
    );
    let archive = add.positional(
        strings(),
        PositionalSpecBuilder { name: s("ARCHIVE") }.options().help(s("The archive to add to.")).build(),
    );
    let files = add.positionals(
        strings(),
        PositionalSpecBuilder { name: s("FILE") }.options().min(1).help(s("Files to add.")).build(),
    );

    let list = cli.subcommand(
        SubcommandSpecBuilder { name: s("list") }
            .options()
            .about(s("List an archive's files."))
            .aliases(Arc::new(vec![s("ls")]))
            .build(),
    );
    let listed = list.positional(
        strings(),
        PositionalSpecBuilder { name: s("ARCHIVE") }.options().help(s("The archive to list.")).build(),
    );

    // Values to run with, text to print (help and version), or a mistake,
    // told apart with `temper_core::cast`.
    let argv: Vec<Arc<String>> = std::env::args().skip(1).map(Arc::new).collect();
    let result = cli.parse(argv, Some(Environment::new(OsEnvironment(Arc::new(())))));
    if let Some(args) = temper_core::cast::<Args>(result.clone()) {
        if args.command() == add {
            let names: Vec<String> = args.get_value(files.clone()).iter().map(|f| f.to_string()).collect();
            println!("add to {}: {}", args.get_value(archive.clone()), names.join(", "));
            let source = args.source(level.param());
            let origin = if source == Source::absent() { s("default") } else { source.name() };
            println!("level: {} ({})", args.get_value(level.clone()), origin);
            println!("mode: {}", args.get_maybe(mode.clone()).unwrap_or_else(|| s("any")));
        } else if args.command() == list {
            println!("list {}", args.get_value(listed.clone()));
        }
        println!("verbose: {}", if args.get_value(verbose.clone()) { "yes" } else { "no" });
    } else if let Some(output) = temper_core::cast::<Output>(result.clone()) {
        print!("{}", output.text(None));
    } else if let Some(error) = temper_core::cast::<ArgError>(result.clone()) {
        eprint!("{}", error.text(None));
    }
    ExitCode::from(result.exit_status() as u8)
}
