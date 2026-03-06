# MQTT IoT

Connect your local MQTT broker to AWS IoT Core for remote monitoring.

<a href="https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/mqtt-iot/template.yaml&stackName=mqtt-iot&capabilities=CAPABILITY_IAM" target="_blank"><img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png" alt="Launch Stack"></a>

## What You Get

- **One-way MQTT bridge**: Local Mosquitto topics are forwarded to AWS IoT Core
- **Publish-only bridge certificate**: Your local broker can only send data, never receive commands
- **Subscribe-only viewer certificate**: Remote clients can only read data, never publish
- **Zero server maintenance**: No EC2 instances to manage

## Prerequisites

- A local Mosquitto MQTT broker running (e.g., on a Raspberry Pi, NAS, or server)

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `TopicPrefix` | Yes | `sensors` | MQTT topic namespace (e.g., `sensors`, `boat`, `home`) |

## Setup

1. Click the "Launch Stack" button above
2. Set your topic prefix (or keep the default `sensors`)
3. Check "I acknowledge..." at the bottom
4. Click **Create stack**
5. Wait for status to show `CREATE_COMPLETE` (1-2 mins)
6. Click the **Outputs** tab

## Connect Your Local Mosquitto

1. Go to the **BridgeCertsLocation** link from the Outputs tab (opens S3 in your browser)
2. Download all files from the `bridge/` folder:
   - `cert.pem` - client certificate
   - `private.key` - private key
   - `root-ca.pem` - Amazon root CA
   - `bridge.conf` - Mosquitto configuration
3. Copy the certificate files to your Mosquitto machine:

```bash
sudo mkdir -p /etc/mosquitto/certs
sudo cp cert.pem private.key root-ca.pem /etc/mosquitto/certs/
sudo cp bridge.conf /etc/mosquitto/conf.d/aws-bridge.conf
```

4. Restart Mosquitto:

```bash
sudo systemctl restart mosquitto
```

Your local MQTT topics under the configured prefix will now be forwarded to AWS IoT Core.

## View Data Remotely

1. Go to the **ViewerCertsLocation** link from the Outputs tab
2. Download all files from the `viewer/` folder:
   - `cert.pem` - client certificate
   - `private.key` - private key
   - `root-ca.pem` - Amazon root CA
3. Copy the **IoTEndpoint** value from the Outputs tab

### MQTT Explorer

1. Open MQTT Explorer and click **+** to add a connection
2. Set **Host** to your IoT endpoint
3. Set **Port** to `8883`
4. Enable **SSL/TLS** and set **Encryption** to `on`
5. Under **Certificate**: select your `root-ca.pem`, `cert.pem`, and `private.key`
6. Click **Connect**
7. You should see topics appearing under your prefix

### MQTTX

1. Click **New Connection**
2. Set **Host** to `mqtts://` followed by your IoT endpoint
3. Set **Port** to `8883`
4. Enable **SSL/TLS**
5. Set **CA File** to `root-ca.pem`
6. Set **Client Certificate File** to `cert.pem`
7. Set **Client Key File** to `private.key`
8. Connect, then add a subscription to `sensors/#` (or your prefix)

## Signal K

If you're using Signal K on a boat or for IoT, the [signalk-aws-iot](https://github.com/sbender9/signalk-aws-iot) plugin connects directly to AWS IoT Core using the bridge certificates.

## Security

This setup enforces one-way data flow at the IAM policy level:

- **Bridge certificate** can only **publish** to your topic prefix. It cannot subscribe or receive messages.
- **Viewer certificate** can only **subscribe and receive**. It cannot publish messages.

This means no commands can ever be sent back to your local network through the bridge. Even if a viewer's certificate is compromised, the attacker can only read sensor data.

## Costs

At typical home/boat usage (a few devices publishing every 5-10 minutes):

- **IoT Core messaging**: ~$0.01/month (charged per million messages)
- **IoT Core connectivity**: ~$0.01/month (charged per million minutes connected)
- **S3 storage**: < $0.01/month (a few KB of certificates)

**Total: ~$0.02/month**

Even at higher volumes (1,000 messages/day), costs stay under $0.10/month. IoT Core pricing only becomes significant at tens of thousands of messages per day.

## Cleanup

To delete and stop charges:

1. Go to [CloudFormation Stacks](https://console.aws.amazon.com/cloudformation/home#/stacks)
2. Select your stack and click **Delete**

All certificates are automatically revoked and the S3 bucket is emptied during deletion. Any connected clients will be disconnected.

## Troubleshooting

**Mosquitto won't start after adding bridge config**

Check the Mosquitto log:
```bash
sudo journalctl -u mosquitto -n 50
```

Make sure all three certificate files exist at the paths in `bridge.conf`.

**"Connection refused" or TLS errors**

- Verify your IoT endpoint is correct (check the Outputs tab)
- Make sure port `8883` is not blocked by your firewall
- Check that `root-ca.pem` is the Amazon root CA, not a self-signed cert

**Messages not appearing in MQTT Explorer**

- Confirm Mosquitto is publishing to topics under your prefix (e.g., `sensors/temperature`, not just `temperature`)
- Check that your subscriber is using the wildcard `sensors/#` (with `#`, not `*`)
- Look at the Mosquitto log for bridge connection status

**`$SYS` topics showing up**

Mosquitto bridges can forward internal `$SYS` topics. The bridge config includes `notifications false` to prevent this, but if you see them, add this to your bridge config:

```
topic # out 1 "" $SYS/
```

This explicitly excludes `$SYS` topics from the bridge.

**Viewer certificate can't connect**

- AWS IoT Core requires TLS 1.2 or higher
- Make sure you're using port `8883`, not `1883`
- Some MQTT apps need the CA, cert, and key files to be in PEM format (they already are from this template)
