#!/bin/bash
# Crea el bucket S3 para el TP. Correr una sola vez.
set -e

BUCKET="soa-frames-tp"
REGION="us-east-1"

echo "Creando bucket $BUCKET en $REGION..."
aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"

# Bloquear acceso público (buena práctica)
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "Bucket creado. Actualizá el .env con:"
echo "  S3_BUCKET_NAME=$BUCKET"
echo "  AWS_REGION=$REGION"
