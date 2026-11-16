// A tour of Argmas, from C++: `pack`, a small archiver's command line.
//
// The same program exists for each language Argmas supports, and they all
// print the same text for the same arguments. See demos/README.md for how
// to run them.

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "argmas/init.hpp"

using argmas::Args;
using argmas::ArgError;
using argmas::Command;
using argmas::CommandSpec;
using argmas::FlagSpec;
using argmas::OptionSpec;
using argmas::Output;
using argmas::PositionalSpec;
using argmas::Source;
using argmas::SubcommandSpec;
using temper::core::NullableParam;
using temper::core::Str;

// Temper's lists are shared vectors.
using Strings = std::vector<Str>;

// The process's environment variables, which Argmas reads through this
// interface, so parsing touches nothing outside on its own.
struct OsEnvironment : argmas::Environment {
  NullableParam<Str> get(Str const & name) const override {
    char const * value = std::getenv(name.c_str());
    if (value == nullptr) {
      return nullptr;
    }
    return Str(value);
  }
};

int main(int argc, char ** argv) {
  // The command, declared once. Each spec's settings go in order, as the
  // Temper class declares them, with nullptr for those left out. Each
  // handle has its type: `level` gives an int32_t and `files` a shared
  // vector of strings.
  auto cli = Command::make(CommandSpec::make("pack", "Pack files into archives.", "1.0.0"));
  // name, short, help, env, negatable, inherited
  auto verbose = cli->flag(FlagSpec::make("verbose", "v", "Say what's happening.", nullptr, nullptr, true));

  // name, about, aliases
  auto add = cli->subcommand(SubcommandSpec::make("add", "Add files to an archive."));
  // name, short, help, env
  auto level = add->optionOr(argmas::ints(), 6, OptionSpec::make("level", "l", "How hard to compress.", "PACK_LEVEL"));
  auto mode = add->option(argmas::choices(std::make_shared<Strings>(Strings{"fast", "small"})), OptionSpec::make("mode", nullptr, "What to favor."));
  // name, help, min
  auto archive = add->positional(argmas::strings(), PositionalSpec::make("ARCHIVE", "The archive to add to."));
  auto files = add->positionals(argmas::strings(), PositionalSpec::make("FILE", "Files to add.", 1));

  auto list = cli->subcommand(SubcommandSpec::make("list", "List an archive's files.", std::make_shared<Strings>(Strings{"ls"})));
  auto listed = list->positional(argmas::strings(), PositionalSpec::make("ARCHIVE", "The archive to list."));

  // Values to run with, text to print (help and version), or a mistake.
  auto result = cli->parse(std::make_shared<Strings>(argv + 1, argv + argc), std::make_shared<OsEnvironment>());
  if (auto args = std::dynamic_pointer_cast<Args>(result)) {
    if (args->get_command()->eq(add)) {
      std::shared_ptr<Strings> paths = args->getValue(files);
      std::string names;
      for (auto const & file : *paths) {
        names += (names.empty() ? "" : ", ") + file.str();
      }
      std::cout << "add to " << args->getValue(archive).str() << ": " << names << "\n";
      auto source = args->source(level->get_param());
      std::string origin = source->eq(Source::absent()) ? "default" : source->name.str();
      std::cout << "level: " << args->getValue(level) << " (" << origin << ")\n";
      NullableParam<Str> chosen = args->getMaybe(mode);
      std::cout << "mode: " << (chosen.has_value ? chosen.value.str() : "any") << "\n";
    } else if (args->get_command()->eq(list)) {
      std::cout << "list " << args->getValue(listed).str() << "\n";
    }
    std::cout << "verbose: " << (args->getValue(verbose) ? "yes" : "no") << "\n";
  } else if (auto output = std::dynamic_pointer_cast<Output>(result)) {
    std::cout << output->text().str();
  } else if (auto error = std::dynamic_pointer_cast<ArgError>(result)) {
    std::cerr << error->text().str();
  }
  return result->get_exitStatus();
}
