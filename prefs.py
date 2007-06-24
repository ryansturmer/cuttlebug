BUILD_COMMAND = "make"

CLEAN_COMMAND = "make clean"

REBUILD_COMMAND = "make clean; make"

ATTACH_COMMAND = "target async localhost:3333"

GDB = "arm-elf-gdb -n -q -i mi"

EXECUTABLE = "build/main.elf"

