# Value types

An option's or positional argument's value arrives as text. A *value
type* turns that text into a typed value, or says what it expected
instead, for the error message. Argmas has `ints`, `floats`, `strings`,
`paths`, `directories`, and `choices([...])`; any other type implements
`ValueType`.

    export interface ValueType<T> {

What a valid value looks like, finishing "expected …" in an error, as
in "invalid value 'abc' for --level: expected an integer".

      public get expected(): String;

The value the text means, or a bubble when it means none.

      public parse(text: String): T throws Bubble;

The text for a value, for defaults in help, so that parsing it gives
the value back.

      public format(value: T): String;

The values allowed, when there's a fixed list, for help and
suggestions; empty when any value that parses is allowed.

      public get choices(): List<String> { [] }

How a shell [completes](complete.temper.md) a value that starts with
`partial`: by default, the choices that start with it, if there's a
list, and nothing otherwise. A type can offer values found when the
program runs, or ask the shell to complete files or directories.

      public complete(partial: String): Completion {
        new Completion(choicesStarting(choices, partial), Directive.none, "")
      }
    }

The choices that start with `partial`, as candidates.

    let choicesStarting(choiceList: List<String>, partial: String): List<Candidate> {
      let out = new ListBuilder<Candidate>();
      for (let c of choiceList) {
        if (startsWith(c, partial)) { out.add(new Candidate(c, "")); }
      }
      out.toList()
    }

## Integers

`ints` takes decimal integers that fit in 32 bits: an optional `+` or
`-`, then ASCII digits, with leading zeros allowed (`007` is 7). No
spaces, underscores, or other bases, so `1_000`, `0x10`, and ` 5` are
errors, the same in every language.

    export let ints: ValueType<Int> = new IntType();

    class IntType extends ValueType<Int> {
      public get expected(): String { "an integer" }

      public parse(text: String): Int throws Bubble {
        let digits = new StringBuilder();
        var negative = false;
        var seenDigit = false;
        var significant = false;
        for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
          let c = text[i];
          if (i == String.begin && (c == char'-' || c == char'+')) {
            negative = c == char'-';
          } else if (c >= char'0' && c <= char'9') {
            seenDigit = true;
            if (c != char'0' || significant) {
              significant = true;
              digits.appendCodePoint(c) orelse panic();
            }
          } else {
            bubble();
          }
        }
        if (!seenDigit) { bubble() }
        let magnitude = digits.toString();
        if (magnitude.isEmpty) { return 0; }
        // Ten digits at most fit, and toInt32 checks the range.
        if (magnitude.hasAtLeast(String.begin, magnitude.end, 11)) { bubble() }
        (if (negative) { "-${magnitude}" } else { magnitude }).toInt32()
      }

      public format(value: Int): String { value.toString() }
    }

## Floats

`floats` takes decimal numbers: an optional sign, digits with an
optional fraction (`1`, `1.5`, `.5`, `5.`), and an optional exponent
(`1e3`, `2.5E-4`). Only finite values are allowed, so `inf`, `NaN`,
and `1e999` are errors.

    export let floats: ValueType<Float64> = new FloatType();

    class FloatType extends ValueType<Float64> {
      public get expected(): String { "a number" }

      public parse(text: String): Float64 throws Bubble {

The text is checked here and rewritten in JSON's number syntax, which
`toFloat64` reads the same way everywhere: no `+`, no leading zeros,
and digits on both sides of a point.

        let json = new StringBuilder();
        var i = String.begin;
        if (text.hasIndex(i) && (text[i] == char'-' || text[i] == char'+')) {
          if (text[i] == char'-') { json.append("-"); }
          i = text.next(i);
        }
        let whole = new StringBuilder();
        var wholeDigits = false;
        while (text.hasIndex(i) && isDigit(text[i])) {
          wholeDigits = true;
          if (text[i] != char'0' || whole.toString() != "") {
            whole.appendCodePoint(text[i]) orelse panic();
          }
          i = text.next(i);
        }
        let wholeText = whole.toString();
        json.append(if (wholeText == "") { "0" } else { wholeText });
        var fractionDigits = false;
        if (text.hasIndex(i) && text[i] == char'.') {
          i = text.next(i);
          let fraction = new StringBuilder();
          while (text.hasIndex(i) && isDigit(text[i])) {
            fraction.appendCodePoint(text[i]) orelse panic();
            fractionDigits = true;
            i = text.next(i);
          }
          if (fractionDigits) { json.append(".${fraction.toString()}"); }
        }
        // `.`, `-`, and `e5` alone aren't numbers.
        if (!wholeDigits && !fractionDigits) { bubble() }
        if (text.hasIndex(i) && (text[i] == char'e' || text[i] == char'E')) {
          json.append("e");
          i = text.next(i);
          if (text.hasIndex(i) && (text[i] == char'-' || text[i] == char'+')) {
            if (text[i] == char'-') { json.append("-"); }
            i = text.next(i);
          }
          var exponentDigits = false;
          while (text.hasIndex(i) && isDigit(text[i])) {
            json.appendCodePoint(text[i]) orelse panic();
            exponentDigits = true;
            i = text.next(i);
          }
          if (!exponentDigits) { bubble() }
        }
        if (text.hasIndex(i)) { bubble() }
        let value = json.toString().toFloat64();
        if (value != value || value == Infinity || value == -Infinity) { bubble() }
        value
      }

      public format(value: Float64): String { value.toString() }
    }

    let isDigit(c: Int): Boolean { c >= char'0' && c <= char'9' }

## Strings

`strings` takes any text, including the empty string. Shells complete
it as files, as they do arguments they know nothing about, since text
arguments are so often paths.

    export let strings: ValueType<String> = new StringType(Directive.files);

## Paths

`paths` and `directories` take any text too, as `strings` does, and
say what it names, so shells complete files or only directories. They
don't check the text: what makes a path valid differs by platform, and
whether it exists may change before the program reads it.

    export let paths: ValueType<String> = new StringType(Directive.files);
    export let directories: ValueType<String> = new StringType(Directive.directories);

    class StringType(private directive: Directive) extends ValueType<String> {
      public get expected(): String { "text" }
      public parse(text: String): String throws Bubble { text }
      public format(value: String): String { value }
      public complete(partial: String): Completion { new Completion([], directive, "") }
    }

## Choices

`choices(["fast", "slow"])` takes exactly one of the given strings,
matched exactly (case matters). Help lists them, and an error suggests
the nearest when there's one close enough.

    export let choices(allowed: List<String>): ValueType<String> {
      new ChoiceType(allowed)
    }

    class ChoiceType(private allowed: List<String>) extends ValueType<String> {
      public get expected(): String { "one of ${allowed.join(", ") { (s: String): String => s }}" }

      public parse(text: String): String throws Bubble {
        for (let s of allowed) {
          if (s == text) { return s; }
        }
        bubble()
      }

      public format(value: String): String { value }
      public get choices(): List<String> { allowed }
    }

## Booleans from the environment

A flag's environment variable holds `1`, `true`, `yes`, or `on` for
true, and `0`, `false`, `no`, or `off` for false, in any ASCII case.
It isn't exported as a value type, since flags take no value on the
command line.

    let parseBoolean(text: String): Boolean throws Bubble {
      let lower = asciiLower(text);
      if (lower == "1" || lower == "true" || lower == "yes" || lower == "on") { return true; }
      if (lower == "0" || lower == "false" || lower == "no" || lower == "off") { return false; }
      bubble()
    }

    let booleanExpected = "true or false";

    let asciiLower(text: String): String {
      let sb = new StringBuilder();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        let c = text[i];
        sb.appendCodePoint(if (c >= char'A' && c <= char'Z') { c + 32 } else { c }) orelse panic();
      }
      sb.toString()
    }
