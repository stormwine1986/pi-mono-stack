#!/usr/bin/env node

const https = require('https');

const API_KEY = process.env.TWITTERAPI_KEY;
const BASE_URL = 'https://api.twitterapi.io';

if (!API_KEY) {
  console.error('Error: TWITTERAPI_KEY environment variable is not set.');
  process.exit(1);
}

function makeRequest(path) {
  return new Promise((resolve, reject) => {
    const url = `${BASE_URL}${path}`;
    const options = {
      headers: {
        'X-API-Key': API_KEY
      }
    };

    https.get(url, options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(new Error(`Failed to parse response: ${data}`));
          }
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    }).on('error', reject);
  });
}

const args = process.argv.slice(2);
const command = args[0];
const target = args[1];

async function main() {
  if (command === 'user' && target) {
    try {
      const data = await makeRequest(`/twitter/user/info?userName=${target}`);
      console.log(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error(err.message);
    }
  } else if (command === 'tweets' && target) {
    try {
      const data = await makeRequest(`/twitter/user/last_tweets?userName=${target}`);
      if (data && data.data && Array.isArray(data.data.tweets)) {
        const filteredTweets = data.data.tweets.map(tweet => ({
          type: tweet.type || 'tweet',
          id: tweet.id,
          url: tweet.url || `https://x.com/i/web/status/${tweet.id}`,
          text: tweet.text,
          is_note_tweet: tweet.is_note_tweet || false,
          note_tweet: tweet.note_tweet,
          createdAt: tweet.createdAt
        }));
        console.log(JSON.stringify({ ...data, data: { ...data.data, tweets: filteredTweets } }, null, 2));
      } else {
        console.log(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      console.error(err.message);
    }
  } else if (command === 'article' && target) {
    try {
      const data = await makeRequest(`/twitter/article?tweet_id=${target}`);
      console.log(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error(err.message);
    }
  } else if (command === 'search' && target) {
    try {
      const data = await makeRequest(`/twitter/tweet/advanced_search?query=${encodeURIComponent(target)}&queryType=Latest`);
      if (data && data.data && Array.isArray(data.data.tweets)) {
        const filteredTweets = data.data.tweets.map(tweet => ({
          type: tweet.type || 'tweet',
          id: tweet.id,
          url: tweet.url || `https://x.com/i/web/status/${tweet.id}`,
          text: tweet.text,
          is_note_tweet: tweet.is_note_tweet || false,
          note_tweet: tweet.note_tweet,
          createdAt: tweet.createdAt
        }));
        console.log(JSON.stringify({ ...data, data: { ...data.data, tweets: filteredTweets } }, null, 2));
      } else {
        console.log(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      console.error(err.message);
    }
  } else {
    console.log('Usage:');
    console.log('  twapi user <username>    - Get user info');
    console.log('  twapi tweets <username>  - Get user last tweets');
    console.log('  twapi article <tweet_id> - Get long article content');
    console.log('  twapi search <query>     - Advanced search (e.g., "from:user since:2024-01-01")');
    process.exit(1);
  }
}

main();
