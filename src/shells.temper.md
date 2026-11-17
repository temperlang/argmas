# Shells

A completion script connects a shell's programmable completion to the
program: as the user types, the shell runs the program with
`__complete` and the words so far, and offers what it prints, as
[completions](complete.temper.md) describes. The scripts are a few
lines each and the same for every program but for its name, so they
needn't change when the program does.

```temper inert
let cli = new Command({ name: "frob", completions: true });
// `frob --completions bash` prints the script, as does:
cli.completionScript(Shell.bash);
```

Argmas only prints scripts: it never edits a user's shell setup. Each
script starts with a comment saying where its shell looks for it:

| Shell | Where the script goes |
|---|---|
| bash (4.4 or later) | `~/.local/share/bash-completion/completions/frob` for the bash-completion package, or sourced from `~/.bashrc` |
| zsh | `_frob` in a directory on `$fpath`, such as `~/.zfunc`, before `compinit` in `~/.zshrc` |
| fish | `~/.config/fish/completions/frob.fish` |
| PowerShell (5.1 or later) | added to the profile, `$PROFILE`, or saved and dot-sourced from it, though not as `frob.ps1` on `PATH`, which PowerShell would run for `frob` |

zsh, fish, and PowerShell show each candidate's description; bash
shows only the candidates. `cmd.exe` has no programmable completion,
so it isn't supported.

    @auto("==")
    export class Shell {
      public name: String;
      private constructor(name: String) { this.name = name; }
      public static bash: Shell = doPure { new Shell("bash") }
      public static zsh: Shell = doPure { new Shell("zsh") }
      public static fish: Shell = doPure { new Shell("fish") }
      public static powershell: Shell = doPure { new Shell("powershell") }

The shell with this name, as `--completions` takes it, or null.

      public static named(name: String): Shell? {
        if (name == "bash") { Shell.bash } else if (name == "zsh") { Shell.zsh } else if (name == "fish") {
          Shell.fish
        } else if (name == "powershell") { Shell.powershell } else { null }
      }

      public toString(): String { name }
    }

The names `--completions` takes, in the order help lists them.

    let shellNames: List<String> = ["bash", "zsh", "fish", "powershell"];

Each script starts with a comment from the command's
[messages](messages.temper.md), `script.bash` and so on.

    let shellScript(shell: Shell, name: String, messages: MessageTable): String {
      let ident = identifier(name);
      let header = commentLines(messages.text("script.${shell.name}", ["program", name]));
      if (shell == Shell.bash) {
        bashScript(header, singleQuoted(name, "'\\''"), ident)
      } else if (shell == Shell.zsh) {
        zshScript(name, header, singleQuoted(name, "'\\''"), ident)
      } else if (shell == Shell.fish) {
        fishScript(header, fishQuoted(name), ident)
      } else {
        powerShellScript(header, singleQuoted(name, "''"), singleQuoted("${name}.exe", "''"))
      }
    }

The program's name made safe for a function's name: ASCII letters and
digits, with anything else as `_`.

    let identifier(name: String): String {
      let sb = new StringBuilder();
      for (var i = String.begin; name.hasIndex(i); i = name.next(i)) {
        let c = name[i];
        let keep = (c >= char'a' && c <= char'z') || (c >= char'A' && c <= char'Z') || isDigit(c);
        sb.appendCodePoint(if (keep) { c } else { char'_' }) orelse panic();
      }
      sb.toString()
    }

The name in single quotes, with each `'` in it written as `escaped`.

    let singleQuoted(name: String, escaped: String): String {
      let sb = new StringBuilder();
      sb.append("'");
      for (var i = String.begin; name.hasIndex(i); i = name.next(i)) {
        if (name[i] == char'\'') {
          sb.append(escaped);
        } else {
          sb.appendCodePoint(name[i]) orelse panic();
        }
      }
      sb.append("'");
      sb.toString()
    }

    let fishQuoted(name: String): String {
      let sb = new StringBuilder();
      sb.append("'");
      for (var i = String.begin; name.hasIndex(i); i = name.next(i)) {
        let c = name[i];
        if (c == char'\'' || c == char'\\') { sb.append("\\"); }
        sb.appendCodePoint(c) orelse panic();
      }
      sb.append("'");
      sb.toString()
    }

## bash

bash's `COMP_WORDS` splits words at `=` and `:` and keeps their
quotes, so the script reads the words from the line itself, up to the
cursor, removing quotes and backslashes as bash will when it runs the
command: `--name "a b` reaches the program as `--name` and `a b`. It
doesn't expand `~` or variables, which the user hasn't run yet. bash
replaces only part of the word being completed, the part after an
open quote, or else after the last `=` or `:` outside quotes, so the
script gives back only that part of each candidate. bash quotes what
it inserts only for file names, so when the word has an open quote or
a candidate has a character the shell would read, such as a space,
the script says its candidates are file names (`compopt -o
filenames`): `my work` goes in as `my\ work`, or inside `"my` as
`"my work"`, closing the quote, whether completed with Tab or all at
once (`insert-completions`). Files and directories, when nothing else
is offered, are bash's own completion, as for any command.

    let bashScript(header: String, quoted: String, ident: String): String {
      """
        "${header}
        "
        "_${ident}_argmas() {
        "    local line=\${COMP_LINE:0:COMP_POINT} words=() word= quote= open=0 started= keep=0 c j
        "    # bash completes only the part of a word after its last = or :.
        "    local breaks=\${COMP_WORDBREAKS//[^=:]/}
        "    # The words as the program gets them, without their quotes and
        "    # backslashes, noting where in the last bash replaces what's typed:
        "    # after an open quote, or else after its last = or : outside quotes.
        "    for (( j = 0; j < \${#line}; j++ )); do
        "        c=\${line:j:1}
        "        if [[ $quote == "'" ]]; then
        "            if [[ $c == "'" ]]; then quote=; else word+=$c; fi
        "        elif [[ $quote == '"' ]]; then
        "            if [[ $c == '"' ]]; then
        "                quote=
        "            elif [[ $c == '\\' && \${line:j+1:1} == [\\"\\\\\\$\\`] ]]; then
        "                word+=\${line:j+1:1}
        "                (( j++ ))
        "            else
        "                word+=$c
        "            fi
        "        elif [[ $c == [[:space:]] ]]; then
        "            [[ -n $started ]] && words+=("$word")
        "            word= started= keep=0
        "        else
        "            started=1
        "            if [[ $c == [\\"\\'] ]]; then
        "                quote=$c open=\${#word}
        "            elif [[ $c == '\\' ]]; then
        "                word+=\${line:j+1:1}
        "                (( j++ ))
        "            else
        "                word+=$c
        "                [[ -n $breaks && $c == ["$breaks"] ]] && keep=\${#word}
        "            fi
        "        fi
        "    done
        "    words+=("$word")
        "    [[ -n $quote ]] && keep=$open
        "    local cur=$word program=\${words[0]} kept=\${word:0:keep}
        "    [[ $program == "~/"* ]] && program=$HOME/\${program:2}
        "    local out lines=() files=() found=() i quoted
        "    out=$("$program" __complete $(( \${#words[@]} - 2 )) "\${words[@]:1}" 2>/dev/null) || return 0
        "    mapfile -t lines <<< "$out"
        "    local directive=\${lines[\${#lines[@]}-1]}
        "    unset 'lines[\${#lines[@]}-1]'
        "    for i in "\${lines[@]}"; do
        "        i=\${i%%$'\\t'*}
        "        [[ -n $i && $i == "$kept"* ]] && found+=("\${i:keep}")
        "    done
        "    case $directive in
        "    :files*|:directories*)
        "        local prefix= option=-f
        "        [[ $directive == *" "* ]] && prefix=\${directive#* }
        "        [[ $directive == :directories* ]] && option=-d
        "        if [[ -z $prefix && \${#found[@]} -eq 0 ]]; then
        "            if [[ $option == -f ]]; then compopt -o default; else compopt -o dirnames; fi
        "            return 0
        "        fi
        "        compopt -o filenames
        "        mapfile -t files < <(compgen "$option" -- "\${cur#"$prefix"}")
        "        for i in "\${files[@]}"; do
        "            i=$prefix$i
        "            [[ $i == "$kept"* ]] && found+=("\${i:keep}")
        "        done
        "        ;;
        "    esac
        "    # bash quotes what it inserts, closing an open quote, when told the
        "    # candidates are file names, as files are; others need that only in
        "    # a quote or when the shell would read some character in them.
        "    for i in "\${found[@]}"; do
        "        printf -v quoted %q "$i"
        "        if [[ -n $quote || $quoted != "$i" ]]; then
        "            compopt -o filenames
        "            break
        "        fi
        "    done
        "    COMPREPLY=("\${found[@]}")
        "    return 0
        "}
        "
        "complete -F _${ident}_argmas ${quoted}
    }

## zsh

The script is an autoloaded completion function, with `#compdef`, or
sourced after `compinit`; candidates and their descriptions go through
`_describe`, and files through `_files`.

    let zshScript(name: String, header: String, quoted: String, ident: String): String {
      """
        "#compdef ${name}
        "${header}
        "
        "_${ident}_argmas() {
        "    local -a lines described
        "    local line directive prefix program=\${(Q)words[1]}
        "    program=\${program/#\\~/$HOME}
        "    lines=("\${(@f)$("$program" __complete $(( CURRENT - 2 )) "\${(@Q)words[2,CURRENT-1]}" "\${(Q)PREFIX}" 2>/dev/null)}")
        "    (( \${#lines} )) || return 1
        "    directive=\${lines[-1]}
        "    lines[-1]=()
        "    for line in $lines; do
        "        [[ -n $line ]] || continue
        "        if [[ $line == *$'\\t'* ]]; then
        "            described+=("\${\${line%%$'\\t'*}//:/\\\\:}:\${line#*$'\\t'}")
        "        else
        "            described+=("\${line//:/\\\\:}")
        "        fi
        "    done
        "    local ret=1
        "    (( \${#described} )) && _describe -t values ${quoted} described && ret=0
        "    case $directive in
        "    :files*|:directories*)
        "        [[ $directive == *' '* ]] && compset -P "\${(b)directive#* }"
        "        if [[ $directive == :files* ]]; then
        "            _files && ret=0
        "        else
        "            _files -/ && ret=0
        "        fi
        "        ;;
        "    esac
        "    return ret
        "}
        "
        "if [[ $zsh_eval_context[-1] == loadautofunc ]]; then
        "    _${ident}_argmas "$@"
        "else
        "    compdef _${ident}_argmas ${quoted}
        "fi
    }

## fish

fish reads `candidate<TAB>description` lines itself, so the script
mostly passes them on, and fish quotes them as it inserts them. Its
`commandline -opc` gives the words before the one being completed
without their quotes, and the script removes that word's own with
`string unescape`, closing an open quote first.

    let fishScript(header: String, quoted: String, ident: String): String {
      """
        "${header}
        "
        "function __${ident}_argmas
        "    set -l words (commandline -opc)
        "    set -l current (commandline -ct)
        "    # The word being completed as the program gets it, without its
        "    # quotes and backslashes, as the other words already are; an open
        "    # quote is closed first.
        "    set -l unquoted
        "    for closing in '' '"' "'"
        "        if set unquoted (string unescape -- "$current$closing" 2>/dev/null)
        "            set current "$unquoted"
        "            break
        "        end
        "    end
        "    set -l arguments $words
        "    set -e arguments[1]
        "    set -l lines ($words[1] __complete (count $arguments) $arguments $current 2>/dev/null)
        "    or return
        "    set -q lines[1]
        "    or return
        "    set -l directive $lines[-1]
        "    set -e lines[-1]
        "    for line in $lines
        "        test -n "$line"
        "        and echo $line
        "    end
        "    set -l prefix (string replace -r '^:\\S+ ?' '' -- $directive)
        "    set -l path (string sub -s (math (string length -- "$prefix") + 1) -- "$current")
        "    switch $directive
        "        case ':files*'
        "            for p in (__fish_complete_path "$path")
        "                echo $prefix$p
        "            end
        "        case ':directories*'
        "            for p in (__fish_complete_directories "$path")
        "                echo $prefix$p
        "            end
        "    end
        "end
        "
        "complete -c ${quoted} -f -a '(__${ident}_argmas)'
    }

## PowerShell

A native argument completer, registered for the name with and without
`.exe`. When it has nothing to offer, PowerShell completes paths, so
a value with no candidates gets paths too, and the script leaves
files to it then; directories it completes itself, keeping only
PowerShell's containers, since PowerShell would offer files too.

    let powerShellScript(header: String, quoted: String, quotedExe: String): String {
      """
        "${header}
        "
        "Register-ArgumentCompleter -Native -CommandName @(${quoted}, ${quotedExe}) -ScriptBlock {
        "    param($wordToComplete, $commandAst, $cursorPosition)
        "    $words = @()
        "    foreach ($element in $commandAst.CommandElements) {
        "        $extent = $element.Extent
        "        if ($extent.StartOffset -ge $cursorPosition) { break }
        "        $text = $extent.Text
        "        if ($extent.EndOffset -gt $cursorPosition) {
        "            $text = $text.Substring(0, $cursorPosition - $extent.StartOffset)
        "        } elseif ($element -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
        "            $text = $element.Value
        "        }
        "        $words += $text
        "    }
        "    $arguments = @($words | Select-Object -Skip 1)
        "    $index = $arguments.Count
        "    if ($wordToComplete -ne '') { $index -= 1 }
        "    $lines = @(& $words[0] __complete $index @arguments 2>$null)
        "    if ($lines.Count -eq 0) { return }
        "    $directive = $lines[-1]
        "    $results = @()
        "    foreach ($line in ($lines | Select-Object -SkipLast 1)) {
        "        if ($line -eq '') { continue }
        "        $value, $description = $line -split "`t", 2
        "        if (-not $description) { $description = $value }
        "        $text = $value
        "        if ($value -match '[\\s''"`$;,(){}|&<>@#]') { $text = "'" + ($value -replace "'", "''") + "'" }
        "        $results += [System.Management.Automation.CompletionResult]::new($text, $value, 'ParameterValue', $description)
        "    }
        "    if ($directive -match '^:(files|directories)(?: (.*))?$') {
        "        $kind = $Matches[1]
        "        $prefix = "$($Matches[2])"
        "        # With nothing else to offer, PowerShell completes files itself,
        "        # but directories only here.
        "        if ($kind -eq 'files' -and $prefix -eq '' -and $results.Count -eq 0) { return }
        "        $part = $wordToComplete.Substring([Math]::Min($prefix.Length, $wordToComplete.Length))
        "        foreach ($path in [System.Management.Automation.CompletionCompleters]::CompleteFilename($part)) {
        "            if ($kind -eq 'directories' -and $path.ResultType -ne 'ProviderContainer') { continue }
        "            $results += [System.Management.Automation.CompletionResult]::new($prefix + $path.CompletionText, $path.ListItemText, $path.ResultType, $path.ToolTip)
        "        }
        "    }
        "    $results
        "}
    }
