# Builds Docker images and uploads them to AWS ECR.
# Skeleton taken from
# https://gist.github.com/mpneuried/0594963ad38e68917ef189b4e6a269db
#
# Depends upon a deploy.env file present in the path with values:
#   APP_NAME=<repo name>
#   AWS_ECR_PROFILE=<name of AWS profile in ~/.aws/credentials that has IAM
#            access upload images to the ECR repository>
#   DOCKER_REPO=<AWS path> in format <id>.dkr.ecr.<region>.amazonaws.com
#   AWS_CLI_REGION=<AWS region name>
#
# Also requires a version.sh script in the path that echoes the version number
# 
# Finally, requires the user to be able to login to AWS through the CLI using credentials saved
# in the path.
# # TODO Allow CI user to authenticate so can deploy automatically

# import deploy config
# You can change the default deploy config with `make cnf="deploy_special.env" release`
dpl ?= deploy.env
include $(dpl)
export $(shell sed 's/=.*//' $(dpl))

# grep the version number from setup.py through helper script
VERSION=$(shell ./version.sh)

# DOCKER TASKS
# Build the container
build: ## Build the container
	docker build -t $(APP_NAME) .

release: build publish ## Make a release by building and publishing the `{version}` and `latest` tagged containers to ECR

# Docker publish
publish: repo-login publish-latest publish-version ## Publish the `{version}` and `latest` tagged containers to ECR

publish-latest: tag-latest ## Publish the `latest` taged container to ECR
	@echo 'publish latest to $(DOCKER_REPO)'
	docker push $(DOCKER_REPO)/$(APP_NAME):latest

publish-version: tag-version ## Publish the `{version}` taged container to ECR
	@echo 'publish $(VERSION) to $(DOCKER_REPO)'
	docker push $(DOCKER_REPO)/$(APP_NAME):$(VERSION)

# Docker tagging
tag: tag-latest tag-version ## Generate container tags for the `{version}` ans `latest` tags

tag-latest: ## Generate container `{version}` tag
	@echo 'create tag latest'
	docker tag $(APP_NAME) $(DOCKER_REPO)/$(APP_NAME):latest

tag-version: ## Generate container `latest` tag
	@echo 'create tag $(VERSION)'
	docker tag $(APP_NAME) $(DOCKER_REPO)/$(APP_NAME):$(VERSION)

# Login to ECR
# Requires user to have login credentials in path
CMD_REPOLOGIN := aws ecr get-login-password --profile $(AWS_ECR_PROFILE) --region $(AWS_CLI_REGION) | docker login --username AWS --password-stdin ${DOCKER_REPO}

repo-login: ## Auto login to AWS-ECR unsing aws-cli
	@eval $(CMD_REPOLOGIN)

version: ## Output the current version
	@echo $(VERSION)
