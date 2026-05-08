dnl GETENV(VAR) - get value of environment variable
define(`GETENV', `esyscmd(`printf "%s" "$$1"')')dnl
define(`IFENV', `ifelse(GETENV($3),`',$1,$2)')dnl

dnl IFCMD(ABSENT, PRESENT, CMD) - if CMD exits 0, use PRESENT else ABSENT
define(`IFCMD', `ifelse(esyscmd(`$3 && echo yes || echo no'),`yes
',`$2',`$1')')dnl
