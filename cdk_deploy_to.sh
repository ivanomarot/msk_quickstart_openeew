#!/usr/bin/bash
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
      -a|--account) ACCOUNT="$2"; shift;;
      -r|--region) REGION="$2"; shift;;
      --debug) set -x;;
      *)
      POSITIONAL+=("$1"); shift;;
  esac
done
set -- "${POSITIONAL[@]}"
[ -z "$ACCOUNT" ] && echo 1>&2 "Provide AWS account." && exit 1
[ -z "$REGION" ] && echo 1>&2 "Provide AWS region." && exit 1
CDK_DEPLOY_ACCOUNT=$ACCOUNT CDK_DEPLOY_REGION=$REGION cdk deploy
exit $?