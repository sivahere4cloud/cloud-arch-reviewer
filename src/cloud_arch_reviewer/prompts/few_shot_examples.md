These examples show the expected depth, tone and honest use of unclear_items. Never copy their content into a real review.

## Example 1: single-AZ web application

Diagram description: Users reach an Application Load Balancer. It forwards traffic to two EC2 instances in a public subnet, both in one Availability Zone. The instances connect to a single RDS MySQL instance in the same zone. Static images are in an S3 bucket. No monitoring or backup components are drawn.

Expected review:

summary: A small three-tier web application with a load balancer, two EC2 instances and one database, all in a single Availability Zone. It suits low traffic but has several single points of failure.

detected_services: Application Load Balancer, EC2 (two instances), RDS MySQL (single instance), S3

pillar_scores:
- Operational Excellence, 2: No monitoring, logging or deployment tooling is shown.
- Security, 2: The app servers sit in a public subnet, and no WAF, security groups or encryption are shown.
- Reliability, 1: Everything runs in one zone and the database has no standby, so a zone failure takes the whole application down.
- Performance Efficiency, 3: The load balancer spreads traffic, but there is no caching or auto scaling.
- Cost Optimization, 3: The footprint is small, but nothing shows right-sizing or pricing choices.
- Sustainability, 3: The setup is simple, and nothing is shown about utilisation.

risks:
- high, Reliability, "Single Availability Zone": A zone outage stops the website and the database. Fix: spread the EC2 instances across at least two Availability Zones and enable Multi-AZ on the RDS instance.
- high, Security, "App servers in a public subnet": The servers are reachable directly from the internet. Fix: move them to private subnets behind the load balancer, and use a NAT gateway or VPC endpoints for outbound access.
- medium, Operational Excellence, "No monitoring": Failures may go unnoticed. Fix: add CloudWatch alarms and centralised logs for the load balancer, instances and database.

unclear_items: Whether the S3 bucket is public or served through CloudFront. Whether RDS automated backups are enabled.

## Example 2: containerised web application across two zones

Diagram description: Users reach CloudFront, protected by AWS WAF. CloudFront forwards to an Application Load Balancer in public subnets across two Availability Zones. The load balancer sends traffic to ECS Fargate tasks in private subnets in both zones. The tasks use an Aurora PostgreSQL cluster with a writer and a reader in different zones, and an ElastiCache Redis cluster for sessions. One NAT gateway provides outbound access. CloudWatch receives logs. The label on the arrow between ECS and Aurora is too blurry to read.

Expected review:

summary: A well-structured containerised web application spread across two zones, with edge protection, private compute and a replicated database. The main gaps are the single NAT gateway and several settings the diagram does not show.

detected_services: CloudFront, AWS WAF, Application Load Balancer, ECS Fargate, Aurora PostgreSQL, ElastiCache Redis, NAT gateway, CloudWatch

pillar_scores:
- Operational Excellence, 4: Logs go to CloudWatch, but no deployment pipeline is shown.
- Security, 4: WAF and private subnets are good practice, but encryption settings cannot be confirmed.
- Reliability, 4: The application and database span two zones, but one NAT gateway is a weak point.
- Performance Efficiency, 4: CloudFront and Redis caching reduce load on the application and database.
- Cost Optimization, 3: No scaling policy or pricing model is shown.
- Sustainability, 3: Fargate helps, but task sizing is not shown.

risks:
- medium, Reliability, "Single NAT gateway": If its zone fails, the tasks in the other zone lose outbound access. Fix: add a NAT gateway in the second zone and route each zone's private subnet to its own.
- low, Operational Excellence, "No deployment pipeline shown": Releases may be manual and hard to repeat. Fix: add an automated pipeline, for example GitHub Actions or CodePipeline, with infrastructure defined as code.
- low, Cost Optimization, "No scaling policy shown": Capacity may be fixed and either wasteful or too small. Fix: enable ECS service auto scaling, and consider a Compute Savings Plan for the steady baseline.

unclear_items: The label on the ECS to Aurora arrow is unreadable, so encryption in transit cannot be confirmed. Aurora backup retention and encryption at rest are not shown.
