build:
	docker build -t malayh/nginx-lb .


release:
	@read -p "Enter Tag:" tag; \
	docker tag malayh/nginx-lb:latest malayh/nginx-lb:$$tag; \
	docker push malayh/nginx-lb:$$tag;