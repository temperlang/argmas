# Argmas in each language

What Argmas's API looks like in each language Temper translates it to,
as the [tours](../demos/README.md) use it, and what reads badly there,
as input for refining the API. In Temper:

```temper
let cli = new Command({ name: "pack", about: "Pack files into archives." });
let add = cli.command({ name: "add" });
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
get in the way.

## C++

```cpp
auto cli = Command::make(CommandSpec::make("pack", "Pack files into archives."));
auto add = cli->command(SubcommandSpec::make("add"));
auto level = add->optionOr(argmas::ints(), 6, OptionSpec::make("level", "l", nullptr, "PACK_LEVEL"));
auto result = cli->parse(std::make_shared<std::vector<Str>>(argv + 1, argv + argc), env);
if (auto args = std::dynamic_pointer_cast<Args>(result)) { args->getValue<int32_t>(level); }
```

- Specs are `make` functions with every setting in order, `nullptr`
  for those left out, so a call needs a comment to be read.
- `getValue` and `getMaybe` take the base handle types (`Arg<T>`), so
  C++ can't deduce `T` from a `Flag` or `Value<T>`, and every read
  names the type: `getValue<bool>(verbose)`.
- Lists are `std::shared_ptr<std::vector<Str>>`; `getMaybe` gives a
  `NullableParam` with `has_value` and `value`; statics and globals
  are functions (`Source::absent()`, `argmas::ints()`); getters mix
  styles (`get_command()`, `get_exitStatus()`).
- `Environment` is a plain abstract class to implement.

## C\#

```csharp
var cli = new Command(new CommandSpec("pack", about: "Pack files into archives."));
var add = cli.Command_(new SubcommandSpec("add"));
var level = add.OptionOr(Ints, 6, new OptionSpec("level", @short: "l", env: "PACK_LEVEL"));
switch (cli.Parse(args, env)) { case Args parsed: parsed.GetValue(level); break; }
```

- Bags are constructors with named arguments, which reads well;
  `short` is `@short`.
- `command` is `Command_`, since a C# method can't share its class's
  name. This reads worst of all the languages.
- `GetMaybe` gives Temper's `Optional<T>`, not `T?`, so a default
  needs `.OrNull() ?? "any"` (with `using TemperLang.Core`).
- Commands compare with `Eq`, not `==`. A program's top-level
  `args` takes the name a parsed result would want.

## Java

```java
var cli = new Command(new CommandSpec.Builder().name("pack").about("Pack files into archives.").build());
var add = cli.command(new SubcommandSpec.Builder().name("add").build());
var level = add.optionOr(ints, 6, new OptionSpec.Builder().name("level").short_("l").env("PACK_LEVEL").build());
if (cli.parse(List.of(argv), System::getenv) instanceof Args args) { args.getValue(level); }
```

- Bags are builders (or constructors with settings in order);
  `short` is a keyword, so its setter is `short_`.
- `Environment` has one method, so `System::getenv` is one.
- Getters are `getCommand()` and `getExitStatus()`, but a handle's
  `param` is a field. Commands compare with `eq`, not `equals`.

## JavaScript

```js
const cli = new Command(CommandSpec.new({ name: "pack", about: "Pack files into archives." }));
const add = cli.command(SubcommandSpec.new({ name: "add" }));
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
local add = cli:command(SubcommandSpec("add"))
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
add = cli.command(SubcommandSpec(name="add"))
level = add.option_or(ints, 6, OptionSpec(name="level", short="l", env="PACK_LEVEL"))
match cli.parse(sys.argv[1:], env):
    case Args() as args: args.get_value(level)
```

- Bags are keyword arguments, and names are snake case
  (`option_or`, `get_value`, `exit_status`).
- `help`, `min`, and `max` are `help_`, `min_`, and `max_`, because
  they're builtins, though argparse users write `help=`.
- `match` works on results, and commands compare with `==`.

## Rust

```rust
let cli = Command::new(CommandSpecBuilder { name: s("pack") }.options().about(s("Pack files into archives.")).build());
let add = cli.command(SubcommandSpecBuilder { name: s("add") }.build());
let level = Arg::new(add.option_or(ints(), 6, OptionSpecBuilder { name: s("level") }.options().env(s("PACK_LEVEL")).build()));
let result = cli.parse(argv, Some(Environment::new(OsEnvironment(Arc::new(())))));
if let Some(args) = temper_core::cast::<Args>(result.clone()) { args.get_value(level.clone()); }
```

- Bags are builders in `argmas::builders`: required settings in a
  struct, then `options()` and a setter for each. Strings are
  `Arc<String>` (`s` above makes one), and the setters, unlike `new`,
  don't take `&str`.
- `get_value` and `get_maybe` take `Arg<T>` and `MaybeArg<T>` by
  value, so concrete handles are wrapped with `Arg::new` and cloned
  for each read.
- Results are told apart with `temper_core::cast`, so the tour
  depends on temper-core too; there's no enum to `match`.
- Implementing `Environment` takes a tuple struct around an `Arc`,
  `clone_boxed`, and `temper_core::impl_any_value_trait!`.
- Commands compare with `==`.

## Worth changing

In Argmas's API:

- **`command` for subcommands.** C#'s `Command_` reads badly, and
  `subcommand` would match `SubcommandSpec` in every language.
- **Handles' declared types.** `flag`, `optionOr`, and the others
  return concrete classes (`Flag`, `Value<T>`); returning `Arg<T>` and
  `MaybeArg<T>` would let C++ deduce `getValue`'s type and spare Rust
  its `Arg::new` wrapping, at no cost in Temper.
- **Matching the command that ran.** `args.command` compared with
  `eq` reads poorly outside Python and Rust; `args.ran(add)` would
  read the same everywhere.

In Temper's translations, not Argmas: Lua's and C++'s positional-only
bags, Python's `help_`, Rust's `Arc<String>` setters, C#'s `Optional`
for `getMaybe`, and JavaScript's `new` taking positional settings.
Generated code also carries the tests' helpers: C++'s `init.hpp`
includes std's testing header, and Rust's crate warns about unused
test helpers when built as a dependency.
