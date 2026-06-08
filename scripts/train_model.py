#!/usr/bin/env python3
"""
Training script for PixelGuard models
Trains encoder, decoder, and discriminator jointly
"""

import argparse
import os
import numpy as np
import tensorflow as tf
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models import Encoder, Decoder, Discriminator
from app.models.noise_layer import CombinedNoiseLayer
from app.utils import MetricsCalculator, ImageProcessor, NoiseProcessor
from app.config import settings


class StegaTrainer:
    """Trainer for steganography models"""
    
    def __init__(self, model_path='./models'):
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        # Models
        self.encoder = Encoder(message_length=settings.MESSAGE_LENGTH)
        self.decoder = Decoder(message_length=settings.MESSAGE_LENGTH)
        self.discriminator = Discriminator()
        self.noise_layer = CombinedNoiseLayer()
        
        # Optimizers
        self.encoder_optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
        self.decoder_optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
        self.discriminator_optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)
        
        # Loss functions
        self.bce_loss = tf.keras.losses.BinaryCrossentropy()
        self.mse_loss = tf.keras.losses.MeanSquaredError()
    
    def reconstruction_loss(self, original, encoded):
        """MSE + adversarial perceptual loss"""
        mse = tf.reduce_mean(tf.square(original - encoded))
        return mse
    
    def message_loss(self, original_message, decoded_message):
        """Binary cross-entropy for message recovery"""
        return self.bce_loss(original_message, decoded_message)
    
    def adversarial_loss(self, discriminator_output, target_label):
        """Adversarial loss from discriminator"""
        return self.bce_loss(tf.ones_like(discriminator_output) * target_label, discriminator_output)
    
    @tf.function
    def train_step(self, cover_images, messages):
        """Single training step"""
        
        # Encode
        with tf.GradientTape() as enc_tape:
            encoded_images = self.encoder([cover_images, messages], training=True)
            
            # Reconstruction loss
            recon_loss = self.reconstruction_loss(cover_images, encoded_images)
            
            # Decoder: extract message
            decoded_messages = self.decoder(encoded_images, training=True)
            msg_loss = self.message_loss(messages, decoded_messages)
            
            # Discriminator fooling loss
            dis_logits = self.discriminator(encoded_images, training=True)
            adv_loss = self.adversarial_loss(dis_logits, 0.0)  # Fool discriminator
            
            # Total encoder loss
            total_loss = recon_loss + msg_loss + 0.01 * adv_loss
        
        # Update encoder
        enc_grads = enc_tape.gradient(total_loss, self.encoder.trainable_variables)
        self.encoder_optimizer.apply_gradients(zip(enc_grads, self.encoder.trainable_variables))
        
        # Decoder loss
        with tf.GradientTape() as dec_tape:
            # Apply noise during training
            noisy_encoded = self.noise_layer(encoded_images, training=True)
            decoded_messages = self.decoder(noisy_encoded, training=True)
            dec_loss = self.message_loss(messages, decoded_messages)
        
        # Update decoder
        dec_grads = dec_tape.gradient(dec_loss, self.decoder.trainable_variables)
        self.decoder_optimizer.apply_gradients(zip(dec_grads, self.decoder.trainable_variables))
        
        # Discriminator loss
        with tf.GradientTape() as dis_tape:
            cover_dis_output = self.discriminator(cover_images, training=True)
            encoded_dis_output = self.discriminator(encoded_images, training=True)
            
            dis_loss = (
                self.bce_loss(tf.ones_like(cover_dis_output), cover_dis_output) +
                self.bce_loss(tf.zeros_like(encoded_dis_output), encoded_dis_output)
            )
        
        # Update discriminator
        dis_grads = dis_tape.gradient(dis_loss, self.discriminator.trainable_variables)
        self.discriminator_optimizer.apply_gradients(zip(dis_grads, self.discriminator.trainable_variables))
        
        return {
            'recon_loss': recon_loss,
            'msg_loss': msg_loss,
            'adv_loss': adv_loss,
            'dis_loss': dis_loss,
        }
    
    def train(self, epochs=10, batch_size=32):
        """Train models"""
        print(f"Starting training for {epochs} epochs with batch size {batch_size}")
        
        for epoch in range(epochs):
            print(f"\nEpoch {epoch + 1}/{epochs}")
            
            # Generate dummy batch for demo
            cover_images = tf.random.uniform((batch_size, settings.IMAGE_SIZE, settings.IMAGE_SIZE, 3))
            messages = tf.random.uniform((batch_size, settings.MESSAGE_LENGTH))
            
            # Train step
            losses = self.train_step(cover_images, messages)
            
            print(f"  Reconstruction Loss: {losses['recon_loss']:.4f}")
            print(f"  Message Loss: {losses['msg_loss']:.4f}")
            print(f"  Adversarial Loss: {losses['adv_loss']:.4f}")
            print(f"  Discriminator Loss: {losses['dis_loss']:.4f}")
        
        # Save models
        self.save_models()
    
    def save_models(self):
        """Save trained models"""
        self.encoder.save_weights(str(self.model_path / 'encoder'))
        self.decoder.save_weights(str(self.model_path / 'decoder'))
        self.discriminator.save_weights(str(self.model_path / 'discriminator'))
        print(f"\nModels saved to {self.model_path}")


def main():
    parser = argparse.ArgumentParser(description='Train PixelGuard models')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=16, help='Batch size')
    parser.add_argument('--model-path', type=str, default='./models', help='Path to save models')
    args = parser.parse_args()
    
    # Check GPU
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"GPUs available: {len(gpus)}")
        for gpu in gpus:
            print(f"  {gpu}")
    else:
        print("No GPU found, using CPU")
    
    # Train
    trainer = StegaTrainer(model_path=args.model_path)
    trainer.train(epochs=args.epochs, batch_size=args.batch_size)


if __name__ == '__main__':
    main()
