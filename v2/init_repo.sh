#!/bin/bash
# Author: BleakNarratives (Kevin Michael Talbert)
# Filename: init_repo.sh
# Extension: .sh
# File Path: ~/mrs_higgins/init_repo.sh
#
# One-shot repo init + first commit for mrs_higgins

cd ~/mrs_higgins
git init
git add mrs_higgins.py README.md
git commit -m "feat: Mrs. Higgins v1.0 — wifi-triggered real-world interface agent"
echo "Repo ready. Push with: git remote add origin <url> && git push -u origin main"
