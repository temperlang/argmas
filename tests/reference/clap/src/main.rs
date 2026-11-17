//! A small program on clap's builder API, for comparing Argmas with it.
//!
//! tests/reference/run.py builds this with cargo and runs it once per
//! case. The spec comes in REFERENCE_SPEC, one argument per line, as
//! run.py describes; the arguments are the program's own. It declares
//! them as a typical clap program does, with clap's defaults otherwise,
//! and prints the result as one line of JSON: the command path and every
//! value, an error's kind, or that help was asked for.
//!
//! clap's error kinds are coarser than Argmas's, so the argument an
//! error names (from clap's `error-context`) tells them apart: an
//! unexpected word is an unknown option when it starts with `-`, and a
//! missing argument a missing option when it does.

use clap::error::{ContextKind, ContextValue, ErrorKind};
use clap::{value_parser, Arg, ArgAction, ArgMatches, Command};

#[derive(Clone, Copy, PartialEq)]
enum Kind {
    Flag,
    Count,
    Negatable,
    On,
    Option,
    Required,
    Repeated,
    Positional,
    Positionals,
}

struct ArgSpec {
    kind: Kind,
    name: &'static str,
    short: Option<char>,
    /// 32 or 64 for integers, 0 for strings.
    int_bits: u32,
    min: usize,
    max: Option<usize>,
}

struct CommandSpec {
    name: &'static str,
    args: Vec<ArgSpec>,
}

/// clap's names are `&'static str` without its `string` feature, and
/// the spec lives as long as the program.
fn leak(s: String) -> &'static str {
    Box::leak(s.into_boxed_str())
}

/// Lines are `command NAME`, or `KIND NAME SHORT TYPE MIN MAX`, with `-`
/// for none; a `command` line after the first starts a subcommand of the
/// first.
fn read_spec(text: &str) -> Vec<CommandSpec> {
    let mut commands: Vec<CommandSpec> = Vec::new();
    for line in text.lines() {
        let words: Vec<&str> = line.split(' ').filter(|w| !w.is_empty()).collect();
        if words.is_empty() {
            continue;
        }
        if words[0] == "command" {
            commands.push(CommandSpec {
                name: leak(words[1].to_owned()),
                args: Vec::new(),
            });
            continue;
        }
        let kind = match words[0] {
            "flag" => Kind::Flag,
            "count" => Kind::Count,
            "negatable" => Kind::Negatable,
            "on" => Kind::On,
            "option" => Kind::Option,
            "required" => Kind::Required,
            "repeated" => Kind::Repeated,
            "positional" => Kind::Positional,
            "positionals" => Kind::Positionals,
            other => panic!("unknown kind {other}"),
        };
        let none = |w: &str| w == "-";
        commands
            .last_mut()
            .expect("a command line first")
            .args
            .push(ArgSpec {
                kind,
                name: leak(words[1].to_owned()),
                short: Some(words[2])
                    .filter(|w| !none(w))
                    .and_then(|w| w.chars().next()),
                int_bits: match words[3] {
                    "int" => 32,
                    "int64" => 64,
                    _ => 0,
                },
                min: words[4].parse().expect("a number"),
                max: Some(words[5])
                    .filter(|w| !none(w))
                    .map(|w| w.parse().expect("a number")),
            });
    }
    commands
}

fn no_name(name: &str) -> &'static str {
    leak(format!("no-{name}"))
}

fn declare(spec: &CommandSpec) -> Command {
    let mut command = Command::new(spec.name);
    for a in &spec.args {
        let name = a.name;
        let mut arg = Arg::new(name);
        if !matches!(a.kind, Kind::Positional | Kind::Positionals) {
            arg = arg.long(name);
            if let Some(short) = a.short {
                arg = arg.short(short);
            }
        }
        match a.int_bits {
            32 => arg = arg.value_parser(value_parser!(i32)),
            64 => arg = arg.value_parser(value_parser!(i64)),
            _ => {}
        }
        arg = match a.kind {
            Kind::Flag => arg.action(ArgAction::SetTrue),
            Kind::Count => arg.action(ArgAction::Count),
            // `--color` and `--no-color`, the last one given winning.
            // When it's on, reading it is reading that `--no-color`
            // isn't set.
            Kind::Negatable | Kind::On => arg.action(ArgAction::SetTrue).overrides_with(no_name(name)),
            Kind::Option => arg.action(ArgAction::Set),
            Kind::Required => arg.action(ArgAction::Set).required(true),
            Kind::Repeated => arg.action(ArgAction::Append),
            Kind::Positional => arg.required(true),
            Kind::Positionals => {
                let arg = arg.action(ArgAction::Append).required(a.min > 0);
                match a.max {
                    Some(max) => arg.num_args(a.min.max(1)..=max),
                    None => arg.num_args(a.min.max(1)..),
                }
            }
        };
        command = command.arg(arg);
        if matches!(a.kind, Kind::Negatable | Kind::On) {
            command = command.arg(
                Arg::new(no_name(name))
                    .long(no_name(name))
                    .action(ArgAction::SetTrue)
                    .overrides_with(name),
            );
        }
    }
    command
}

fn json_string(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn value(a: &ArgSpec, matches: &ArgMatches) -> String {
    let id = a.name;
    let one = |m: &ArgMatches| -> String {
        if a.int_bits == 32 {
            m.get_one::<i32>(id)
                .map_or("null".to_owned(), |n| n.to_string())
        } else if a.int_bits == 64 {
            m.get_one::<i64>(id)
                .map_or("null".to_owned(), |n| n.to_string())
        } else {
            m.get_one::<String>(id)
                .map_or("null".to_owned(), |s| json_string(s))
        }
    };
    let many = |m: &ArgMatches| -> String {
        let items: Vec<String> = if a.int_bits == 32 {
            m.get_many::<i32>(id)
                .into_iter()
                .flatten()
                .map(|n| n.to_string())
                .collect()
        } else if a.int_bits == 64 {
            m.get_many::<i64>(id)
                .into_iter()
                .flatten()
                .map(|n| n.to_string())
                .collect()
        } else {
            m.get_many::<String>(id)
                .into_iter()
                .flatten()
                .map(|s| json_string(s))
                .collect()
        };
        format!("[{}]", items.join(", "))
    };
    match a.kind {
        Kind::Flag | Kind::Negatable => matches.get_flag(id).to_string(),
        Kind::On => (!matches.get_flag(no_name(id))).to_string(),
        Kind::Count => matches.get_count(id).to_string(),
        Kind::Repeated | Kind::Positionals => many(matches),
        _ => one(matches),
    }
}

/// The argument an error is about, as clap shows it, such as
/// `--output <output>` or `<FILE>`.
fn invalid_arg(error: &clap::Error) -> String {
    match error.get(ContextKind::InvalidArg) {
        Some(ContextValue::String(s)) => s.clone(),
        Some(ContextValue::Strings(v)) => v.first().cloned().unwrap_or_default(),
        _ => String::new(),
    }
}

fn error_kind(error: &clap::Error) -> String {
    let arg = invalid_arg(error);
    let is_option = arg.starts_with('-') && arg != "-";
    match error.kind() {
        ErrorKind::DisplayHelp | ErrorKind::DisplayHelpOnMissingArgumentOrSubcommand => {
            return "help".to_owned();
        }
        ErrorKind::UnknownArgument if is_option => "unknownOption",
        ErrorKind::UnknownArgument => "tooManyPositionals",
        ErrorKind::InvalidSubcommand => "unknownCommand",
        ErrorKind::MissingSubcommand => "missingCommand",
        ErrorKind::MissingRequiredArgument if is_option => "missingRequired",
        ErrorKind::MissingRequiredArgument => "tooFewPositionals",
        // An empty value where one is needed: none given.
        ErrorKind::InvalidValue
            if matches!(error.get(ContextKind::InvalidValue), Some(ContextValue::String(s)) if s.is_empty()) =>
        {
            "missingValue"
        }
        ErrorKind::InvalidValue | ErrorKind::ValueValidation => "invalidValue",
        ErrorKind::TooManyValues if is_option => "unexpectedValue",
        ErrorKind::TooManyValues => "tooManyPositionals",
        ErrorKind::TooFewValues | ErrorKind::WrongNumberOfValues => "tooFewPositionals",
        // The specs declare no conflicts, so this is an option or flag
        // given twice, which clap refuses unless told otherwise; Argmas
        // has no such error.
        ErrorKind::ArgumentConflict => "givenTwice",
        kind => return format!("unclassified ({kind:?})"),
    }
    .to_owned()
}

fn main() {
    let Ok(text) = std::env::var("REFERENCE_SPEC") else {
        eprintln!("REFERENCE_SPEC isn't set");
        std::process::exit(3);
    };
    let specs = read_spec(&text);
    let (top, subs) = specs.split_first().expect("a command");
    let mut command = declare(top);
    if !subs.is_empty() {
        command = command.subcommand_required(true);
        for sub in subs {
            command = command.subcommand(declare(sub));
        }
    }
    let matches = match command.try_get_matches_from(std::env::args_os()) {
        Ok(matches) => matches,
        Err(error) => {
            let kind = error_kind(&error);
            if kind == "help" {
                println!("{{\"output\": \"help\"}}");
            } else {
                println!("{{\"error\": {}}}", json_string(&kind));
            }
            return;
        }
    };
    let mut path = vec![top.name];
    let mut values: Vec<String> = top
        .args
        .iter()
        .map(|a| format!("{}: {}", json_string(a.name), value(a, &matches)))
        .collect();
    if let Some((name, sub_matches)) = matches.subcommand() {
        let sub = subs
            .iter()
            .find(|s| s.name == name)
            .expect("a declared subcommand");
        path.push(sub.name);
        values.extend(
            sub.args
                .iter()
                .map(|a| format!("{}: {}", json_string(a.name), value(a, sub_matches))),
        );
    }
    println!(
        "{{\"command\": {}, \"values\": {{{}}}}}",
        json_string(&path.join(" ")),
        values.join(", ")
    );
}
