-- A tour of Argmas, from Lua: `pack`, a small archiver's command line.
--
-- The same program exists for each language Argmas supports, and they all
-- print the same text for the same arguments. See demos/README.md for how
-- to run them.

local argmas = require("argmas")
local Command, CommandSpec, SubcommandSpec = argmas.Command, argmas.CommandSpec, argmas.SubcommandSpec
local FlagSpec, OptionSpec, PositionalSpec = argmas.FlagSpec, argmas.OptionSpec, argmas.PositionalSpec
local Args, Output, ArgError, Source = argmas.Args, argmas.Output, argmas.ArgError, argmas.Source
local ints, strings, choices = argmas.ints, argmas.strings, argmas.choices
local temper = require("temper-core")

-- The command, declared once. Lua has no named arguments, so each spec's
-- settings go in order, as the Temper class declares them, with nil for
-- those left out.
local cli = Command(CommandSpec("pack", "Pack files into archives.", "1.0.0"))
-- name, short, help, env, negatable, inherited
local verbose = cli:flag(FlagSpec("verbose", "v", "Say what's happening.", nil, nil, true))

local add = cli:subcommand(SubcommandSpec("add", "Add files to an archive."))
-- name, short, help, env
local level = add:optionOr(ints, 6, OptionSpec("level", "l", "How hard to compress.", "PACK_LEVEL"))
local mode = add:option(choices({ "fast", "small" }), OptionSpec("mode", nil, "What to favor."))
-- name, help, min
local archive = add:positional(strings, PositionalSpec("ARCHIVE", "The archive to add to."))
local files = add:positionals(strings, PositionalSpec("FILE", "Files to add.", 1))

-- name, about, aliases
local list = cli:subcommand(SubcommandSpec("list", "List an archive's files.", { "ls" }))
local listed = list:positional(strings, PositionalSpec("ARCHIVE", "The archive to list."))

-- Argmas reads environment variables through a table with `get`, so
-- parsing touches nothing outside on its own.
local env = { get = function(_, name) return os.getenv(name) end }

-- Values to run with, text to print (help and version), or a mistake.
local result = cli:parse({ ... }, env)
if temper.instance_of(result, Args) then
  local args = result
  if args.command:eq(add) then
    print(("add to %s: %s"):format(args:getValue(archive), table.concat(args:getValue(files), ", ")))
    local source = args:source(level.param)
    local origin = source:eq(Source.absent) and "default" or source.name
    print(("level: %d (%s)"):format(args:getValue(level), origin))
    -- A missing value is temper.null, which is truthy, so null_to_nil
    -- makes it nil.
    print("mode: " .. (temper.null_to_nil(args:getMaybe(mode)) or "any"))
  elseif args.command:eq(list) then
    print("list " .. args:getValue(listed))
  end
  print("verbose: " .. (args:getValue(verbose) and "yes" or "no"))
elseif temper.instance_of(result, Output) then
  io.stdout:write(result:text())
elseif temper.instance_of(result, ArgError) then
  io.stderr:write(result:text())
end
os.exit(result.exitStatus)
