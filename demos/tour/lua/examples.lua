-- The site's section examples, from Lua.
--
-- Each `snippet:` block is shown on the site under its section, beside the
-- same example in every other language; demos/run.py runs this program in
-- each language and checks it prints demos/tour/examples.txt.

local argmas = require("argmas")
local Command, CommandSpec, SubcommandSpec = argmas.Command, argmas.CommandSpec, argmas.SubcommandSpec
local FlagSpec, OptionSpec, PositionalSpec = argmas.FlagSpec, argmas.OptionSpec, argmas.PositionalSpec
local Output, ArgError, Style = argmas.Output, argmas.ArgError, argmas.Style
local ints, strings, choices, paths, directories = argmas.ints, argmas.strings, argmas.choices, argmas.paths, argmas.directories
local temper = require("temper-core")

-- snippet: styles
local function frob(style)
  -- name, about, version, commandOptional, style
  local cli = Command(CommandSpec("frob", "Frobnicate files.", nil, nil, style))
  cli:flag(FlagSpec("verbose", "v", "Say more."))
  cli:optionOr(ints, 3, OptionSpec("level", "l", "How hard."))
  cli:positionals(strings, PositionalSpec("FILE", "Files to frobnicate."))
  return cli
end

local gnu = frob(Style.gnu)
local go = frob(Style.singleDash)
local windows = frob(Style.windows)
-- end snippet

-- snippet: subcommands
local git = Command(CommandSpec("minigit", "Track files."))
-- name, short, help, env, negatable, inherited
local quiet = git:flag(FlagSpec("quiet", "q", "Say less.", nil, nil, true))
local repo = git:option(directories, OptionSpec("dir", nil, "Where the repository is."))

local add = git:subcommand(SubcommandSpec("add", "Add files."))
local force = add:flag(FlagSpec("force", "f", "Add ignored files too."))
-- name, help, min
local added = add:positionals(paths, PositionalSpec("PATH", "Files to add.", 1))

-- name, about, aliases
local rm = git:subcommand(SubcommandSpec("rm", "Remove files.", { "remove" }))
-- end snippet

-- snippet: completions
-- name, about, version, commandOptional, style, alsoStyle, completions
local cli = Command(CommandSpec("frob", nil, nil, nil, nil, nil, true))
cli:flag(FlagSpec("verbose", "v", "Say more."))
cli:option(choices({ "fast", "slow" }), OptionSpec("mode", nil, "How to go about it."))
cli:option(paths, OptionSpec("out", nil, "Where to write."))
-- end snippet

-- snippet: messages
local function frobWith(messages)
  local cli = Command(CommandSpec("frob", "Frobnicate files."))
  cli:optionOr(ints, 3, OptionSpec("level", "l", "How hard."))
  -- setMessages takes Temper's map type, so a loop over a table is simpler.
  for key, template in pairs(messages) do
    cli:setMessage(key, template)
  end
  return cli
end

local english = frobWith({})
-- A partial translation: what isn't set stays English.
local german = frobWith({
  ["usage"] = "Aufruf: {command}",
  ["usage.options"] = "[OPTIONEN]",
  ["help.options"] = "Optionen:",
  ["help.default"] = "[Vorgabe: {value}]",
  ["error.unknownOption.suggest"] = "unbekannte Option {option}; meinten Sie {suggestion}?",
  ["error.tryHelp"] = "Mehr dazu mit '{command} {help}'.",
})
-- A typo in a key is a mistake in the spec, found on the first run.
local typo = frobWith({ usge = "Aufruf: {command}" })
-- end snippet

-- Parses a command line's words after the program's name, split at spaces,
-- and prints the line, any text Argmas gives, and the exit status.
local function show(command, line)
  local words = {}
  for word in line:gmatch("%S+") do
    words[#words + 1] = word
  end
  table.remove(words, 1)
  local result = command:parse(words)
  io.stdout:write("$ ", line, "\n")
  if temper.instance_of(result, Output) or temper.instance_of(result, ArgError) then
    io.stdout:write(result:text())
  end
  io.stdout:write(("(exit status %d)\n\n"):format(result.exitStatus))
end

show(gnu, "frob --help")
show(gnu, "frob --level=high a.txt")
show(go, "frob -help")
show(go, "frob -level=high a.txt")
show(windows, "frob /?")
show(windows, "frob /level:high a.txt")
show(git, "minigit -q add a.txt")
show(git, "minigit help add")
show(git, "minigit ad a.txt")
show(git, "minigit add --dir repo a.txt")
show(cli, "frob --help")
show(cli, "frob __complete 0 --mo")
show(cli, "frob __complete 1 --mode f")
show(english, "frob --levle 5")
show(german, "frob --help")
show(german, "frob --levle 5")
show(typo, "frob --help")
