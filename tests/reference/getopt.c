/* A small program on glibc's getopt_long, for comparing Argmas with it.

   tests/reference/run.py compiles this with the system's cc and runs it
   once per case. The spec comes in REFERENCE_SPEC, one argument per line,
   as run.py describes; the arguments are the program's own. It parses
   them as a typical getopt_long program does, stopping at the first
   error, and prints the result as one line of JSON: the command path and
   every value, an error's kind, or that help was asked for.

   What getopt_long doesn't do itself (counting positional arguments,
   checking integers and required options, and subcommands, which stop
   options at the first word with a leading `+` and parse the rest
   again) is done here, as programs on getopt_long do it. */

#define _GNU_SOURCE
#include <errno.h>
#include <getopt.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX 64
#define HELP_VAL 1000
#define FIRST_VAL 2000

enum kind { FLAG, COUNT, NEGATABLE, ON, OPTION, REQUIRED, REPEATED, POSITIONAL, POSITIONALS };

struct arg {
  enum kind kind;
  char *name;
  int short_name; /* 0 when none */
  int int_bits; /* 32 or 64 for integers, 0 for strings */
  int min, max; /* positionals; max -1 for no limit */
  /* What was found. */
  int count;
  char *value;
  char *values[MAX];
  int n_values;
};

struct command {
  char *name;
  struct arg args[MAX];
  int n_args;
  struct command *subs[MAX];
  int n_subs;
};

static struct command commands[MAX];
static int n_commands;

static void fail(const char *kind) {
  printf("{\"error\": \"%s\"}\n", kind);
  exit(0);
}

static void json_string(const char *s) {
  putchar('"');
  for (; *s; s++) {
    unsigned char c = (unsigned char)*s;
    if (c == '"' || c == '\\') {
      printf("\\%c", c);
    } else if (c < 0x20) {
      printf("\\u%04x", c);
    } else {
      putchar(c);
    }
  }
  putchar('"');
}

static enum kind kind_named(const char *word) {
  static const char *names[] = {"flag", "count", "negatable", "on", "option", "required", "repeated", "positional", "positionals"};
  for (int i = 0; i < 9; i++) {
    if (strcmp(word, names[i]) == 0) return (enum kind)i;
  }
  fprintf(stderr, "unknown kind %s\n", word);
  exit(3);
}

/* Lines are `command NAME`, or KIND NAME SHORT TYPE MIN MAX, with `-`
   for none; a `command` line after the first starts a subcommand of the
   first. */
static void read_spec(char *text) {
  for (char *line = strtok(text, "\n"); line; line = strtok(NULL, "\n")) {
    char *words[6] = {0};
    int n = 0;
    for (char *save, *w = strtok_r(line, " ", &save); w && n < 6; w = strtok_r(NULL, " ", &save)) {
      words[n++] = w;
    }
    if (n == 0) continue;
    if (strcmp(words[0], "command") == 0) {
      struct command *c = &commands[n_commands++];
      c->name = words[1];
      if (n_commands > 1) commands[0].subs[commands[0].n_subs++] = c;
      continue;
    }
    struct command *c = &commands[n_commands - 1];
    struct arg *a = &c->args[c->n_args++];
    a->kind = kind_named(words[0]);
    a->name = words[1];
    a->short_name = n > 2 && strcmp(words[2], "-") != 0 ? words[2][0] : 0;
    a->int_bits = n < 4 ? 0 : strcmp(words[3], "int") == 0 ? 32 : strcmp(words[3], "int64") == 0 ? 64 : 0;
    /* A flag that's on is set until --no-NAME. */
    a->count = a->kind == ON;
    a->min = n > 4 ? atoi(words[4]) : 0;
    a->max = n > 5 && strcmp(words[5], "-") != 0 ? atoi(words[5]) : -1;
  }
}

static void check_int(const char *text, int bits) {
  char *end;
  errno = 0;
  long long n = strtoll(text, &end, 10);
  if (*text == '\0' || *end != '\0' || errno || (bits == 32 && (n < INT_MIN || n > INT_MAX))) fail("invalidValue");
}

static void take_value(struct arg *a, char *value) {
  if (a->int_bits) check_int(value, a->int_bits);
  if (a->kind == REPEATED) {
    a->values[a->n_values++] = value;
  } else {
    a->value = value;
  }
}

/* Parses one command's arguments, argv[0] being its name, and returns
   the subcommand chosen, if any, with its arguments left in argv. */
static struct command *parse(struct command *c, int argc, char **argv, int *rest) {
  struct option longs[2 * MAX + 2];
  int n_longs = 0;
  char shorts[3 * MAX + 4];
  int n_shorts = 0;
  int by_short[256];
  for (int i = 0; i < 256; i++) by_short[i] = -1;
  /* `+` stops at the first non-option when there are subcommands, and
     `:` reports a missing value apart from an unknown option. */
  if (c->n_subs) shorts[n_shorts++] = '+';
  shorts[n_shorts++] = ':';
  shorts[n_shorts++] = 'h';
  longs[n_longs++] = (struct option){"help", no_argument, NULL, HELP_VAL};
  for (int i = 0; i < c->n_args; i++) {
    struct arg *a = &c->args[i];
    if (a->kind == POSITIONAL || a->kind == POSITIONALS) continue;
    int takes = a->kind == OPTION || a->kind == REQUIRED || a->kind == REPEATED;
    longs[n_longs++] = (struct option){a->name, takes ? required_argument : no_argument, NULL, FIRST_VAL + 2 * i};
    if (a->kind == NEGATABLE || a->kind == ON) {
      char *no = malloc(strlen(a->name) + 4);
      sprintf(no, "no-%s", a->name);
      longs[n_longs++] = (struct option){no, no_argument, NULL, FIRST_VAL + 2 * i + 1};
    }
    if (a->short_name) {
      shorts[n_shorts++] = (char)a->short_name;
      if (takes) shorts[n_shorts++] = ':';
      by_short[a->short_name] = i;
    }
  }
  longs[n_longs] = (struct option){0};
  shorts[n_shorts] = '\0';

  /* 0 starts glibc's getopt afresh, for each command. */
  optind = 0;
  opterr = 0;
  int found;
  int index;
  while ((found = getopt_long(argc, argv, shorts, longs, &index)) != -1) {
    if (found == 'h' || found == HELP_VAL) {
      printf("{\"output\": \"help\"}\n");
      exit(0);
    }
    if (found == ':') fail("missingValue");
    if (found == '?') {
      /* optopt is the option for a short option, or a long option given
         a value it doesn't take, and 0 for an unknown or ambiguous long
         option, which getopt_long has already stepped past. */
      if (optopt >= FIRST_VAL || optopt == HELP_VAL) fail("unexpectedValue");
      if (optopt == 0) {
        const char *word = argv[optind - 1] + 2;
        size_t length = strcspn(word, "=");
        int matches = 0;
        for (int i = 0; i < n_longs; i++) {
          if (strncmp(longs[i].name, word, length) == 0) matches++;
        }
        fail(matches > 1 ? "ambiguousOption" : "unknownOption");
      }
      fail("unknownOption");
    }
    int i = found >= FIRST_VAL ? (found - FIRST_VAL) / 2 : by_short[found];
    struct arg *a = &c->args[i];
    switch (a->kind) {
      case FLAG: a->count = 1; break;
      case COUNT: a->count++; break;
      case NEGATABLE:
      case ON: a->count = found >= FIRST_VAL && (found - FIRST_VAL) % 2 ? 0 : 1; break;
      default: take_value(a, optarg); break;
    }
  }

  struct command *sub = NULL;
  if (c->n_subs) {
    if (optind >= argc) fail("missingCommand");
    for (int i = 0; i < c->n_subs; i++) {
      if (strcmp(c->subs[i]->name, argv[optind]) == 0) sub = c->subs[i];
    }
    if (!sub) fail("unknownCommand");
    *rest = optind;
  } else {
    /* Positional arguments, each list getting its minimum and the rest
       going to the earliest that takes more. */
    int given = argc - optind;
    int need = 0;
    int room = 0;
    for (int i = 0; i < c->n_args; i++) {
      struct arg *a = &c->args[i];
      if (a->kind == POSITIONAL) { need += 1; room = room < 0 ? -1 : room + 1; }
      if (a->kind == POSITIONALS) {
        need += a->min;
        room = room < 0 || a->max < 0 ? -1 : room + a->max;
      }
    }
    if (given < need) fail("tooFewPositionals");
    if (room >= 0 && given > room) fail("tooManyPositionals");
    int extra = given - need;
    for (int i = 0; i < c->n_args; i++) {
      struct arg *a = &c->args[i];
      if (a->kind == POSITIONAL) take_value(a, argv[optind++]);
      if (a->kind == POSITIONALS) {
        int more = a->max < 0 ? extra : a->max - a->min < extra ? a->max - a->min : extra;
        extra -= more;
        for (int k = 0; k < a->min + more; k++) {
          if (a->int_bits) check_int(argv[optind], a->int_bits);
          a->values[a->n_values++] = argv[optind++];
        }
      }
    }
  }
  return sub;
}

static void check_required(struct command *c) {
  for (int i = 0; i < c->n_args; i++) {
    if (c->args[i].kind == REQUIRED && !c->args[i].value) fail("missingRequired");
  }
}

static void print_value(struct arg *a) {
  json_string(a->name);
  printf(": ");
  switch (a->kind) {
    case FLAG:
    case NEGATABLE:
    case ON: printf(a->count ? "true" : "false"); break;
    case COUNT: printf("%d", a->count); break;
    case REPEATED:
    case POSITIONALS:
      putchar('[');
      for (int k = 0; k < a->n_values; k++) {
        if (k) printf(", ");
        if (a->int_bits) printf("%lld", strtoll(a->values[k], NULL, 10)); else json_string(a->values[k]);
      }
      putchar(']');
      break;
    default:
      if (!a->value) printf("null");
      else if (a->int_bits) printf("%lld", strtoll(a->value, NULL, 10));
      else json_string(a->value);
  }
}

int main(int argc, char **argv) {
  char *spec = getenv("REFERENCE_SPEC");
  if (!spec) {
    fprintf(stderr, "REFERENCE_SPEC isn't set\n");
    return 3;
  }
  read_spec(strdup(spec));
  struct command *path[MAX];
  int depth = 0;
  path[depth++] = &commands[0];
  int rest = 0;
  struct command *sub = parse(&commands[0], argc, argv, &rest);
  if (sub) {
    path[depth++] = sub;
    parse(sub, argc - rest, argv + rest, &rest);
  }
  for (int d = 0; d < depth; d++) check_required(path[d]);

  printf("{\"command\": \"");
  for (int d = 0; d < depth; d++) printf(d ? " %s" : "%s", path[d]->name);
  printf("\", \"values\": {");
  int first = 1;
  for (int d = 0; d < depth; d++) {
    for (int i = 0; i < path[d]->n_args; i++) {
      if (!first) printf(", ");
      first = 0;
      print_value(&path[d]->args[i]);
    }
  }
  printf("}}\n");
  return 0;
}
