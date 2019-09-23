import boto3
import sys
import json
import time

if __name__ == "__main__":
    bucket_name = sys.argv[1]
    print("Applying policy to bucket: {0}".format(bucket_name))
    client = boto3.client('s3')

    # Get and modify Block public access (bucket settings) of the bucket
    resp = client.get_public_access_block(Bucket=bucket_name)
    public_access_block_config = resp['PublicAccessBlockConfiguration']
    public_access_block_config['BlockPublicPolicy'] = False

    resp = client.put_public_access_block(Bucket=bucket_name,
                                          PublicAccessBlockConfiguration=public_access_block_config)

    # time needed for the permissions change to take effect
    time.sleep(10)

    # Attach required policy for CDN usage to the bucket
    policy = {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "PublicReadForGetBucketObjects",
          "Action": [
            "s3:GetObject",
          ],
          "Effect": "Allow",
          "Resource": "arn:aws:s3:::{S3_UPLOADS_BUCKET_NAME}/*".format(S3_UPLOADS_BUCKET_NAME=bucket_name),
          "Principal": "*"
        }
      ]
    }
    policy = json.dumps(policy)

    response = client.put_bucket_policy(
        Bucket=bucket_name,
        Policy=policy
    )
