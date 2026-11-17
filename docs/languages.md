# Argmas in each language

What Argmas's API looks like in each language Temper translates it to,
as the [tours](../demos/README.md) use it, and what reads badly there,
as input for refining the API. In Temper:

```temper
let cli = new Command({ name: "pack", about: "Pack files into archives." });
let add = cli.subcommand({ name: "add" });
let level = add.optionOr(ints, 6, { name: "level", short: "l", env: "PACK_LEVEL" });
when (cli.parse(argv, env)) {
  is Args -> ...;     // args.get(level), an Int
  is Output -> ...;   // help or version: print, exit 0
  is ArgError -> ...; // print to standard error, exit 2
}
```

Everywhere, `args.get(h)` is two methods, `getValue` for handles that
always have a value and `getMaybe` for options that may be absent, as
the [design](design.md#temper-constraints-met-so-far) explains, and
`ints`, `strings`, and `choices` are named so no language's keywords
get in the way. Declaring an argument (`flag`, `optionOr`, and the
rest) returns `Arg<T>` or `MaybeArg<T>`, the types `getValue` and
`getMaybe` take, so each language knows the value's type from the
handle's.

## C++

```cpp
auto cli = Command::make(CommandSpec::make("pack", "Pack files into archives."));
auto add = cli->subcommand(SubcommandSpec::make("add"));
auto level = add->optionOr(argmas::ints(), 6, OptionSpec::make("level", "l", nullptr, "PACK_LEVEL"));
auto result = cli->parse(std::make_shared<std::vector<Str>>(argv + 1, argv + argc), env);
if (auto args = std::dynamic_pointer_cast<Args>(result)) { args->getValue(level); }
```

- Specs are `make` functions with every setting in order, `nullptr`
  for those left out, so a call needs a comment to be read.
- Handles are `std::shared_ptr<Arg<T>>`, so `getValue(level)` deduces
  its type, an `int32_t`.
- Lists are `std::shared_ptr<std::vector<Str>>`; `getMaybe` gives a
  `NullableParam` with `has_value` and `value`; statics and globals
  are functions (`Source::absent()`, `argmas::ints()`); getters mix
  styles (`get_command()`, `get_exitStatus()`, `get_param()`).
- `Environment` is a plain abstract class to implement.

## C\#

```csharp
var cli = new Command(new CommandSpec("pack", about: "Pack files into archives."));
var add = cli.Subcommand(new SubcommandSpec("add"));
var level = add.OptionOr(Ints, 6, new OptionSpec("level", @short: "l", env: "PACK_LEVEL"));
switch (cli.Parse(args, env)) { case Args parsed: parsed.GetValue(level); break; }
```

- Bags are constructors with named arguments, which reads well;
  `short` is `@short`.
- `GetMaybe` gives Temper's `Optional<T>`, not `T?`, so a default
  needs `.OrNull() ?? "any"` (with `using TemperLang.Core`).
- Commands compare with `Eq`, not `==`. A program's top-level
  `args` takes the name a parsed result would want.

## Java

```java
var cli = new Command(new CommandSpec.Builder().name("pack").about("Pack files into archives.").build());
var add = cli.subcommand(new SubcommandSpec.Builder().name("add").build());
var level = add.optionOr(ints, 6, new OptionSpec.Builder().name("level").short_("l").env("PACK_LEVEL").build());
if (cli.parse(List.of(argv), System::getenv) instanceof Args args) { args.getValue(level); }
```

- Bags are builders (or constructors with settings in order);
  `short` is a keyword, so its setter is `short_`.
- `Environment` has one method, so `System::getenv` is one.
- Getters are `getCommand()`, `getExitStatus()`, and a handle's
  `getParam()`. Commands compare with `eq`, not `equals`.

## JavaScript

```js
const cli = new Command(CommandSpec.new({ name: "pack", about: "Pack files into archives." }));
const add = cli.subcommand(SubcommandSpec.new({ name: "add" }));
const level = add.optionOr(ints, 6, OptionSpec.new({ name: "level", short: "l", env: "PACK_LEVEL" }));
const result = cli.parse(process.argv.slice(2), { get: (name) => process.env[name] ?? null });
if (result instanceof Args) { result.getValue(level); }
```

- Bags are object literals through each class's static `new`; `new
  FlagSpec({ ... })`, which JavaScript users will try first, takes
  the settings in order and quietly makes the whole object the name.
- Any object with `get` serves as the environment.
- Commands compare with `.eq()`.

## Lua

```lua
local cli = Command(CommandSpec("pack", "Pack files into archives."))
local add = cli:subcommand(SubcommandSpec("add"))
local level = add:optionOr(ints, 6, OptionSpec("level", "l", nil, "PACK_LEVEL"))
local result = cli:parse({ ... }, { get = function(_, name) return os.getenv(name) end })
if temper.instance_of(result, Args) then result:getValue(level) end
```

- Specs take every setting in order, `nil` for those left out, with no
  table-of-names form, so they need comments to be read.
- Results are told apart with temper-core's `instance_of`, and an
  absent value is `temper.null`, which is truthy, so `getMaybe` needs
  `temper.null_to_nil` before `or`.
- Any table with `get` serves as the environment.

## Python

```python
cli = Command(CommandSpec(name="pack", about="Pack files into archives."))
add = cli.subcommand(SubcommandSpec(name="add"))
level = add.option_or(ints, 6, OptionSpec(name="level", short="l", env="PACK_LEVEL"))
match cli.parse(sys.argv[1:], env):
    case Args() as args: args.get_value(level)
```

- Bags are keyword arguments, and names are snake case
  (`option_or`, `get_value`, `exit_status`).
- Settings keep their plain names, builtins included, so `help=`,
  `min=`, and `max=` read as in argparse. Only hard keywords would
  take a trailing `_`, and no setting meets one.
- `match` works on results, and commands compare with `==`.

## Rust

```rust
let cli = Command::new(CommandSpecBuilder { name: s("pack") }.options().about(s("Pack files into archives.")).build());
let add = cli.subcommand(SubcommandSpecBuilder { name: s("add") }.build());
let level = add.option_or(ints(), 6, OptionSpecBuilder { name: s("level") }.options().env(s("PACK_LEVEL")).build());
let result = cli.parse(argv, Some(Environment::new(OsEnvironment(Arc::new(())))));
if let Some(args) = temper_core::cast::<Args>(result.clone()) { args.get_value(level.clone()); }
```

- Bags are builders in `argmas::builders`: required settings in a
  struct, then `options()` and a setter for each. Strings are
  `Arc<String>` (`s` above makes one), and the setters, unlike `new`,
  don't take `&str`.
- `get_value` and `get_maybe` take `Arg<T>` and `MaybeArg<T>` by
  value, so a handle read more than once is cloned for each read.
- Results are told apart with `temper_core::cast`, so the tour
  depends on temper-core too; there's no enum to `match`.
- Implementing `Environment` takes a tuple struct around an `Arc`,
  `clone_boxed`, and `temper_core::impl_any_value_trait!`.
- Commands compare with `==`.

## Messages

A program's own [messages](design.md#messages) read the same way
everywhere: `setMessage(key, template)` takes two strings
(`set_message` in Python and Rust, with `Arc<String>`s in Rust, and
`SetMessage` in C#). `setMessages`, for a whole table, takes the
language's own map in Python (any `Mapping`, such as a `dict`), Java
(`Map`), C# (`IReadOnlyDictionary`), and JavaScript (`Map`), but
Temper's map types in C++, Lua, and Rust, where a loop calling
`setMessage` is simpler:

```python
cli.set_messages({"usage": "Aufruf: {command}", "help.options": "Optionen:"})
```

```lua
for key, template in pairs(GERMAN) do cli:setMessage(key, template) end
```

## Worth changing

Changed already: subcommands are declared with `subcommand`, matching
`SubcommandSpec` (it was `command`, which C# made `Command_`), and
declaring an argument returns `Arg<T>` or `MaybeArg<T>` rather than
classes such as `Flag` and `Value<T>`, so C++ deduces `getValue`'s
type and Rust needs no `Arg::new`.

In Argmas's API:

- **Names renamed for keywords.** One setting still meets keywords:
  `short` is `short_` in C++ and Java and `@short` in C#. It's the
  usual name (clap's too), and `shortName` would be longer
  everywhere, so it stays. No method or class name collides any more.

In Temper's translations, not Argmas: Lua's and C++'s positional-only
bags; Rust's `Arc<String>` setters; C#'s `Optional` for `getMaybe`; and
JavaScript's `new` taking positional settings. Commands compare with
an `eq` method outside Python and Rust because tempest translates a
user-defined `@operator("==")` to that method rather than to each
language's own equality (C#'s and C++'s `==`, Java's `equals`, Lua's
`__eq`); that's a planned tempest fix, after which `args.command ==
add` reads naturally wherever the language allows it (JavaScript has
no user-defined equality). Generated code also carries the tests'
helpers: C++'s `init.hpp` includes std's testing header, and Rust's
crate warns about unused test helpers when built as a dependency.
