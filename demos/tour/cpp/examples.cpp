// The site's section examples, from C++.
//
// Each `snippet:` block is shown on the site under its section, beside the
// same example in every other language; demos/run.py runs this program in
// each language and checks it prints demos/tour/examples.txt.

#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "argmas/init.hpp"

using argmas::ArgError;
using argmas::Command;
using argmas::CommandSpec;
using argmas::FlagSpec;
using argmas::OptionSpec;
using argmas::Output;
using argmas::PositionalSpec;
using argmas::Style;
using argmas::SubcommandSpec;
using temper::core::Str;

// Temper's lists are shared vectors.
using Strings = std::vector<Str>;

// snippet: styles
std::shared_ptr<Command> frob(std::shared_ptr<Style> const & style) {
  // name, about, version, commandOptional, style
  auto cli = Command::make(CommandSpec::make("frob", "Frobnicate files.", nullptr, nullptr, style));
  // name, short, help
  cli->flag(FlagSpec::make("verbose", "v", "Say more."));
  cli->optionOr(argmas::ints(), 3, OptionSpec::make("level", "l", "How hard."));
  // name, help
  cli->positionals(argmas::strings(), PositionalSpec::make("FILE", "Files to frobnicate."));
  return cli;
}
// end snippet

// snippet: messages
std::shared_ptr<Command> frobWith(std::map<std::string, std::string> const & messages) {
  auto cli = Command::make(CommandSpec::make("frob", "Frobnicate files."));
  cli->optionOr(argmas::ints(), 3, OptionSpec::make("level", "l", "How hard."));
  // setMessages takes Temper's map type, so a loop is simpler.
  for (auto const & message : messages) {
    cli->setMessage(message.first, message.second);
  }
  return cli;
}
// end snippet

// Parses a command line's words after the program's name, split at spaces,
// and prints the line, any text Argmas gives, and the exit status.
void show(std::shared_ptr<Command> const & command, std::string const & line) {
  auto words = std::make_shared<Strings>();
  std::istringstream split(line);
  std::string word;
  split >> word;
  while (split >> word) {
    words->push_back(word);
  }
  auto result = command->parse(words);
  std::cout << "$ " << line << "\n";
  if (auto output = std::dynamic_pointer_cast<Output>(result)) {
    std::cout << output->text().str();
  } else if (auto error = std::dynamic_pointer_cast<ArgError>(result)) {
    std::cout << error->text().str();
  }
  std::cout << "(exit status " << result->get_exitStatus() << ")\n\n";
}

int main() {
  // snippet: styles
  auto gnu = frob(Style::gnu());
  auto go = frob(Style::singleDash());
  auto windows = frob(Style::windows());
  // end snippet

  // snippet: subcommands
  auto git = Command::make(CommandSpec::make("minigit", "Track files."));
  // name, short, help, env, negatable, inherited
  auto quiet = git->flag(FlagSpec::make("quiet", "q", "Say less.", nullptr, nullptr, true));
  auto repo = git->option(argmas::directories(), OptionSpec::make("dir", nullptr, "Where the repository is."));

  // name, about, aliases
  auto add = git->subcommand(SubcommandSpec::make("add", "Add files."));
  auto force = add->flag(FlagSpec::make("force", "f", "Add ignored files too."));
  // name, help, min
  auto added = add->positionals(argmas::paths(), PositionalSpec::make("PATH", "Files to add.", 1));

  auto rm = git->subcommand(SubcommandSpec::make("rm", "Remove files.", std::make_shared<Strings>(Strings{"remove"})));
  // end snippet

  // snippet: completions
  // name, about, version, commandOptional, style, alsoStyle, completions
  auto cli = Command::make(CommandSpec::make("frob", nullptr, nullptr, nullptr, Style::gnu(), nullptr, true));
  cli->flag(FlagSpec::make("verbose", "v", "Say more."));
  cli->option(argmas::choices(std::make_shared<Strings>(Strings{"fast", "slow"})), OptionSpec::make("mode", nullptr, "How to go about it."));
  cli->option(argmas::paths(), OptionSpec::make("out", nullptr, "Where to write."));
  // end snippet

  // snippet: messages
  auto english = frobWith({});
  // A partial translation: what isn't set stays English.
  auto german = frobWith({
      {"usage", "Aufruf: {command}"},
      {"usage.options", "[OPTIONEN]"},
      {"help.options", "Optionen:"},
      {"help.default", "[Vorgabe: {value}]"},
      {"error.unknownOption.suggest", "unbekannte Option {option}; meinten Sie {suggestion}?"},
      {"error.tryHelp", "Mehr dazu mit '{command} {help}'."},
  });
  // A typo in a key is a mistake in the spec, found on the first run.
  auto typo = frobWith({{"usge", "Aufruf: {command}"}});
  // end snippet

  show(gnu, "frob --help");
  show(gnu, "frob --level=high a.txt");
  show(go, "frob -help");
  show(go, "frob -level=high a.txt");
  show(windows, "frob /?");
  show(windows, "frob /level:high a.txt");
  show(git, "minigit -q add a.txt");
  show(git, "minigit help add");
  show(git, "minigit ad a.txt");
  show(git, "minigit add --dir repo a.txt");
  show(cli, "frob --help");
  show(cli, "frob __complete 0 --mo");
  show(cli, "frob __complete 1 --mode f");
  show(english, "frob --levle 5");
  show(german, "frob --help");
  show(german, "frob --levle 5");
  show(typo, "frob --help");
  return 0;
}
