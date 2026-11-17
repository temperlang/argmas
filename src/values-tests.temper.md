# Value type tests

Each value type's accepted text, the same in every language. The
helpers parse with a type, giving a marker value when it fails.

    let showInt(text: String): String { (ints.parse(text) orelse -999).toString() }
    let fl(text: String): Float64 { floats.parse(text) orelse -1.0 }
    let okFloat(text: String): Boolean { do { floats.parse(text); true } orelse false }
    let str(type: ValueType<String>, text: String): String { type.parse(text) orelse "(no)" }

## Integers

    test("integers") {
      assert(showInt("0") == "0");
      assert(showInt("42") == "42");
      assert(showInt("-42") == "-42");
      assert(showInt("+42") == "42");
      assert(showInt("007") == "7");
      assert(showInt("-0") == "0");
      assert(showInt("0000000000000001") == "1");
      assert(showInt("2147483647") == "2147483647");
      assert(showInt("-2147483648") == "-2147483648");
    }

    test("not integers") {
      for (let text of [
        "", "-", "+", " 5", "5 ", "1_000", "0x10", "1e3", "1.0", "--5", "+-5", "five",
        "2147483648", "-2147483649", "99999999999", "٣",
      ]) {
        assert(showInt(text) == "-999") { "'${text}' is not an integer" }
      }
    }

`ints64` takes the same text, within 64 bits.

    let showInt64(text: String): String { (ints64.parse(text) orelse -999i64).toString() }

    test("64-bit integers") {
      assert(showInt64("0") == "0");
      assert(showInt64("-42") == "-42");
      assert(showInt64("+007") == "7");
      assert(showInt64("-0") == "0");
      assert(showInt64("2147483648") == "2147483648");
      assert(showInt64("-2147483649") == "-2147483649");
      assert(showInt64("5000000000") == "5000000000");
      assert(showInt64("9223372036854775807") == "9223372036854775807");
      assert(showInt64("-9223372036854775808") == "-9223372036854775808");
      assert(showInt64("00009223372036854775807") == "9223372036854775807");
      assert((ints64.parse("9007199254740993") orelse 0i64) == 9007199254740993i64);
      assert(ints64.expected == "an integer");
    }

    test("not 64-bit integers") {
      for (let text of [
        "", "-", "+", " 5", "1_000", "0x10", "1e3", "1.0", "--5", "five",
        "9223372036854775808", "-9223372036854775809", "9223372036854775810",
        "18446744073709551616", "99999999999999999999", "٣",
      ]) {
        assert(showInt64(text) == "-999") { "'${text}' is not a 64-bit integer" }
      }
    }

Options and positional arguments take them as any other type, with
the same errors, and a default in help.

    test("64-bit options") {
      let cli = new Command({ name: "dd" });
      let size = cli.optionOr(ints64, 4294967296i64, { name: "size", short: "s", help: "How many bytes.", env: "DD_SIZE" });
      let skip = cli.option(ints64, { name: "skip" });
      let offsets = cli.positionals(ints64, { name: "OFFSET" });
      let none = cli.parse([]) as Args orelse panic();
      assert(none.get(size) == 4294967296i64);
      assert(none.get(skip) == null);
      let args = cli.parse(["-s", "-9223372036854775808", "--skip=8589934592", "1", "-5000000000"]) as Args orelse panic();
      assert(args.get(size) == -9223372036854775807i64 - 1i64);
      assert((args.get(skip) ?? 0i64) == 8589934592i64);
      let offsetList = args.get(offsets);
      assert(offsetList.length == 2 && offsetList[0] == 1i64 && offsetList[1] == -5000000000i64);
      let fromEnv = cli.parse([], new MapEnvironment(new Map([new Pair("DD_SIZE", "9223372036854775807")]))) as Args orelse panic();
      assert(fromEnv.get(size) == 9223372036854775807i64);
      assert(outcome(cli.parse(["--size=9223372036854775808"])) == "invalidValue: invalid value '9223372036854775808' for --size: expected an integer");
      assert(outcome(cli.parse(["x"])) == "invalidValue: invalid value 'x' for OFFSET: expected an integer");
      assert(contains(cli.help(), "How many bytes. [default: 4294967296] [env: DD_SIZE]"));
      assert(ints64.format(-9223372036854775807i64 - 1i64) == "-9223372036854775808");
    }

## Floats

    test("floats") {
      assert(fl("0") == 0.0);
      assert(fl("1.5") == 1.5);
      assert(fl("-1.5") == -1.5);
      assert(fl("+2") == 2.0);
      assert(fl(".5") == 0.5);
      assert(fl("5.") == 5.0);
      assert(fl("007.25") == 7.25);
      assert(fl("1e3") == 1000.0);
      assert(fl("2.5E-1") == 0.25);
      assert(fl("1e+2") == 100.0);
      assert(fl("-.5e1") == -5.0);
    }

    test("not floats") {
      for (let text of [
        "", ".", "-", "-.", "e3", ".e3", "1e", "1e+", "1.2.3", " 1", "1 ", "1,5",
        "inf", "Infinity", "-Infinity", "NaN", "1e999", "0x1p3", "1_0",
      ]) {
        assert(!okFloat(text)) { "'${text}' is not a float" }
      }
    }

## Strings and choices

    test("strings") {
      assert(str(strings, "") == "");
      assert(str(strings, " a b ") == " a b ");
      assert(strings.expected == "text");
      assert(strings.choices.isEmpty);
    }

    test("choices") {
      let c = choices(["fast", "slow"]);
      assert(str(c, "fast") == "fast");
      assert(str(c, "FAST") == "(no)");
      assert(str(c, "") == "(no)");
      assert(c.expected == "one of fast, slow");
      assert(c.choices.length == 2);
    }

## Booleans from the environment

    test("booleans") {
      for (let t of ["1", "true", "TRUE", "Yes", "on"]) {
        assert(parseBoolean(t) orelse false) { "'${t}' is true" }
      }
      for (let t of ["0", "false", "No", "OFF"]) {
        assert(!(parseBoolean(t) orelse true)) { "'${t}' is false" }
      }
      for (let t of ["", "y", "2", " true"]) {
        assert(do { parseBoolean(t); false } orelse true) { "'${t}' is neither" }
      }
    }

## Formatting defaults

`format` gives text that parses back to the same value.

    test("formatting") {
      assert(ints.format(-3) == "-3");
      assert(floats.format(0.5) == "0.5");
      assert(floats.format(2.0) == "2.0");
      assert(floats.format(-1500.0) == "-1500.0");
      assert(fl(floats.format(1.0e25)) == 1.0e25);
      assert(strings.format("a b") == "a b");
    }

## A value type of the program's own

Any class implementing `ValueType` works as an option's type, with its
own message.

    class Port extends ValueType<Int> {
      public get expected(): String { "a port number from 1 to 65535" }
      public parse(text: String): Int throws Bubble {
        let n = ints.parse(text);
        if (n < 1 || n > 65535) { bubble() }
        n
      }
      public format(value: Int): String { value.toString() }
    }

    test("a custom value type") {
      let cli = new Command({ name: "serve" });
      let port = cli.optionOr(new Port(), 8080, { name: "port", short: "p" });
      let args = cli.parse(["-p", "443"]) as Args orelse panic();
      assert(args.get(port) == 443);
      assert(outcome(cli.parse(["-p", "0"])) == "invalidValue: invalid value '0' for --port: expected a port number from 1 to 65535");
      assert(contains(cli.help(), "[default: 8080]"));
    }
