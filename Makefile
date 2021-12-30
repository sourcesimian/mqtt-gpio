REGISTRY=
REPO=sourcesimian/mqtt-gpio
TAG=$(shell cat version)

check:
	flake8 ./mqtt_gpio --ignore E501
	find ./mqtt_gpio -name '*.py' \
	| xargs pylint -d invalid-name \
	               -d locally-disabled \
	               -d missing-docstring \
	               -d too-few-public-methods \
	               -d line-too-long \
	               -d no-self-use \
	               -d too-many-arguments

test:
	pytest ./tests/ -vvv --junitxml=./reports/unittest-results.xml

docker-armv6:
	$(eval REPOTAG := ${REGISTRY}${REPO}:${TAG}-armv6)
	docker buildx build \
	    --platform linux/arm/v6 \
	    --load \
	    -t ${REPOTAG} \
	    -f docker/Dockerfile.alpine \
	    .

push: docker-armv6
	$(eval REPOTAG := ${REGISTRY}${REPO}:${TAG})
	$(eval LATEST := ${REGISTRY}${REPO}:latest)
	docker push ${REPOTAG}-armv6

	docker manifest create \
	    ${REPOTAG} \
	    --amend ${REPOTAG}-armv6
	docker manifest push ${REPOTAG}

	docker manifest create \
	    ${LATEST} \
	    --amend ${REPOTAG}-armv6
	docker manifest push ${LATEST}

run-armv6:
	docker run -it --rm -p 8080:8080 ${REGISTRY}${REPO}:${TAG}-armv6
