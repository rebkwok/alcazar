# Alcazar Makefile

#------------------------------------------------------------------------------

default:
	echo hello

dirtytests: export PYTHONPATH = $(HOME)/docs/prog/record
dirtytests:
	./run-tests.sh

test : dirtytests clean

clean:
	find -name '*.pyc' -delete
	find -name '__pycache__' -delete

#------------------------------------------------------------------------------
