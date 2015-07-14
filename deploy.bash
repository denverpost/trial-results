#!/bin/bash
source source.bash
python verdict.py 
./ftp.bash --dir $REMOTE_DIR/output --host $REMOTE_HOST
# Run it twice.
sleep 20
python verdict.py 
./ftp.bash --dir $REMOTE_DIR/output --host $REMOTE_HOST
#./ftp.bash --dir $REMOTE_DIR --source_dir www --host $REMOTE_HOST
