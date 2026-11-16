# Argument styles

A command's `style` chooses how its options are written. The same spec
drives parsing, help, and usage lines in each style:

| Style | Looks like | Common in |
|---|---|---|
| `Style.gnu` (default) | `-v`, `-abc`, `--verbose`, `--out=f` | most Unix tools |
| `Style.singleDash` | `-verbose`, `-out=f`, `-out f` | Go's `flag`, Java's tools |
| `Style.windows` | `/v`, `/out:f`, `/out f`, `/?` | Windows tools |

```temper inert
let cli = new Command({ name: "frob", style: Style.windows });
let verbose = cli.flag({ name: "verbose", short: "v" });
// `frob /v`, `frob /VERBOSE`, `frob -verbose`, and `frob --verbose`
// all set it, and `frob /?` gives the help.
```

- **`gnu`:** `--name`, `--name=value`, and `--name value`; `-v`,
  bundles (`-vq`), and `-ofile`, as the
  [parser](parse.temper.md#the-parser) describes.
- **`singleDash`:** `-name`, `-name=value`, and `-name value`, where
  the name is a long or a short one, so `-abc` is one name, not a
  bundle, and `-ofile` is an unknown option, not `-o file`. `--name`
  is the same as `-name`, as in Go's `flag`.
- **`windows`:** `/name`, `/name:value`, `/name=value`, and
  `/name value` (as in `taskkill /pid 42`), with a long or short name;
  `-name` and `--name` work the same, as in most current Windows
  tools. Names ignore ASCII case (`/V`, `/Verbose`), as Windows tools
  do; values and subcommands' names don't. `/?` (and `-?`) asks for
  help, as do `/help` and `/h`.

And in every style:

- `--` alone ends options, `-` alone is a positional argument, and a
  negatable flag is turned off with `no-` before its name (`--no-color`,
  `-no-color`, or `/no-color`).
- A separate value can't look like an option, as in `gnu`, so it can't
  start with `-` (other than `-` alone and numbers), nor, in `windows`,
  be `/` and the name of an option; attached values take anything.
- **Numbers:** in `singleDash` and `windows`, an argument like `-5` or
  `-1.5` is an option only if it's the name of one; otherwise it's a
  value. (In `gnu`, a short option that's a digit makes every such
  argument an option, as in argparse.)
- **`/` in `windows`:** `/word` is an option only when `word` (before
  any `:` or `=`) is the name of one, `no-` and a negatable flag's
  name, or a built-in (`?`, `h`, `help`, `version`). Other words
  starting with `/` are positional arguments, so `/usr/bin/x` works as
  a path, unless the command takes no positional arguments; then
  they're unknown options, with suggestions. To pass a path that is
  also an option's name, give it after `--`.
- **Names in `singleDash` and `windows`** share one namespace, so a
  long name can't also be another option's short name, and in
  `windows` no two names may differ only in case; the spec reports
  either as declared twice.

A command may accept two styles at once, for a tool moving from one to
the other: `alsoStyle` names the second. An argument is read in the
first style in which it names a known option (or a built-in), and an
argument neither knows is reported in the first style that would take
it as an option at all. Help, usage lines, and messages naming options
use the first style. Subcommands take their top command's styles.

    @auto("==")
    export class Style {
      public name: String;

How help writes a long name (`--`, `-`, or `/`), and a short one.

      public prefix: String;
      public shortPrefix: String;

What joins an attached value in help and messages: `=` or `:`.

      public joiner: String;

      private constructor(name: String, prefix: String, shortPrefix: String, joiner: String) {
        this.name = name;
        this.prefix = prefix;
        this.shortPrefix = shortPrefix;
        this.joiner = joiner;
      }

      public static gnu: Style = doPure { new Style("gnu", "--", "-", "=") }
      public static singleDash: Style = doPure { new Style("singleDash", "-", "-", "=") }
      public static windows: Style = doPure { new Style("windows", "/", "/", ":") }

Whether names match ignoring ASCII case.

      public get ignoresCase(): Boolean { name == "windows" }

Whether long and short names share one namespace, each read after a
single prefix.

      public get oneNamespace(): Boolean { name != "gnu" }

      public toString(): String { name }
    }

## Reading an argument in a style

How an argument splits into the prefix, the name, and an attached
value, in `singleDash` or `windows`; null when it isn't shaped like an
option in that style.

    class Named(public prefix: String, public name: String, public inline: String?) {}

    let splitNamed(arg: String, style: Style): Named? {
      var prefix = "";
      if (startsWith(arg, "--")) {
        prefix = "--";
      } else if (startsWith(arg, "-")) {
        prefix = "-";
      } else if (style == Style.windows && startsWith(arg, "/")) {
        prefix = "/";
      } else {
        return null;
      }
      let body = dropFirst(arg, codePointCount(prefix));
      if (body.isEmpty) { return null; }
      var end = body.end;
      var valueStart: StringIndex? = null;
      for (var i = String.begin; body.hasIndex(i); i = body.next(i)) {
        let c = body[i];
        if (c == char'=' || (c == char':' && style == Style.windows)) {
          end = i;
          valueStart = body.next(i);
          break;
        }
      }
      let start = valueStart;
      let inline = if (start != null) { body.slice(start, body.end) } else { null };
      new Named(prefix, body.slice(String.begin, end), inline)
    }

Whether two names match, ignoring ASCII case when asked.

    let sameName(a: String, b: String, ignoreCase: Boolean): Boolean {
      if (ignoreCase) { asciiLower(a) == asciiLower(b) } else { a == b }
    }

    let asciiLower(text: String): String {
      let sb = new StringBuilder();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        let c = text[i];
        sb.appendCodePoint(if (c >= char'A' && c <= char'Z') { c + 32 } else { c }) orelse panic();
      }
      sb.toString()
    }
